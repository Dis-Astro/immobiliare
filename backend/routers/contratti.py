from fastapi import APIRouter, HTTPException, Depends, Query
from typing import List, Optional
from datetime import date, datetime, timezone
from dateutil.relativedelta import relativedelta
from motor.motor_asyncio import AsyncIOMotorDatabase

from models.contratto import Contratto, ContrattoCreate, ContrattoUpdate, StatoContratto, Periodicita, ReminderConfig
from models.rata import Rata, StatoRata
from models.user import UserInDB, UserRole
from routers.auth import get_current_user, get_db
from services.audit import log_audit

router = APIRouter(prefix="/contratti", tags=["Contratti"])


def generate_rate(contratto: Contratto) -> List[dict]:
    """Genera rate per il contratto."""
    rate = []
    
    # Determina numero di rate
    if contratto.periodicita == Periodicita.MENSILE:
        num_rate = contratto.durata_mesi
        delta = relativedelta(months=1)
    elif contratto.periodicita == Periodicita.TRIMESTRALE:
        num_rate = contratto.durata_mesi // 3
        delta = relativedelta(months=3)
    else:  # ANNUALE
        num_rate = contratto.durata_mesi // 12
        delta = relativedelta(years=1)
    
    current_date = contratto.data_inizio
    
    for i in range(num_rate):
        # Calcola data scadenza rata
        scadenza = date(current_date.year, current_date.month, min(contratto.giorno_scadenza, 28))
        
        rata = Rata(
            contratto_id=contratto.id,
            periodo=scadenza.strftime("%Y-%m"),
            importo=contratto.canone_importo,
            stato=StatoRata.DA_INCASSARE,
            data_scadenza=scadenza
        )
        
        rata_dict = rata.model_dump()
        rata_dict["created_at"] = rata_dict["created_at"].isoformat()
        rata_dict["data_scadenza"] = rata_dict["data_scadenza"].isoformat() if rata_dict["data_scadenza"] else None
        
        rate.append(rata_dict)
        current_date = current_date + delta
    
    return rate


@router.get("", response_model=List[Contratto])
async def list_contratti(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    stato: Optional[StatoContratto] = None,
    unita_id: Optional[str] = None,
    affittuario_id: Optional[str] = None,
    scadenza_entro_giorni: Optional[int] = None,
    search: Optional[str] = None,
    current_user: UserInDB = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """Lista contratti con filtri."""
    query = {}
    if stato:
        query["stato"] = stato
    if unita_id:
        query["unita_id"] = unita_id
    if affittuario_id:
        query["affittuario_id"] = affittuario_id
    if search:
        query["$or"] = [
            {"codice_contratto": {"$regex": search, "$options": "i"}},
            {"note": {"$regex": search, "$options": "i"}}
        ]
    if scadenza_entro_giorni:
        target_date = (date.today() + relativedelta(days=scadenza_entro_giorni)).isoformat()
        query["data_scadenza"] = {"$lte": target_date}
        query["stato"] = "attivo"
    
    contratti = await db.contratti.find(query, {"_id": 0}).skip(skip).limit(limit).to_list(limit)
    
    # Enrich with related data
    for c in contratti:
        unita = await db.unita.find_one({"id": c["unita_id"]}, {"_id": 0, "codice_unita": 1, "immobile_id": 1})
        if unita:
            c["unita_codice"] = unita["codice_unita"]
            immobile = await db.immobili.find_one({"id": unita["immobile_id"]}, {"_id": 0, "titolo": 1})
            c["immobile_titolo"] = immobile["titolo"] if immobile else None
        
        locatore = await db.soggetti.find_one({"id": c["locatore_id"]}, {"_id": 0, "nome": 1})
        c["locatore_nome"] = locatore["nome"] if locatore else None
        
        affittuario = await db.soggetti.find_one({"id": c["affittuario_id"]}, {"_id": 0, "nome": 1})
        c["affittuario_nome"] = affittuario["nome"] if affittuario else None
        
        # Get affittuario rating
        valutazioni = await db.valutazioni_affittuari.find(
            {"affittuario_id": c["affittuario_id"]},
            {"_id": 0, "score_pagamenti": 1}
        ).to_list(10)
        if valutazioni:
            c["affittuario_rating"] = sum(v.get("score_pagamenti", 100) for v in valutazioni) / len(valutazioni)
    
    return contratti


@router.get("/count")
async def count_contratti(
    stato: Optional[StatoContratto] = None,
    current_user: UserInDB = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """Conta contratti."""
    query = {}
    if stato:
        query["stato"] = stato
    count = await db.contratti.count_documents(query)
    return {"count": count}


@router.post("", response_model=Contratto)
async def create_contratto(
    data: ContrattoCreate,
    current_user: UserInDB = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """Crea nuovo contratto e genera rate."""
    if current_user.ruolo == UserRole.LETTURA:
        raise HTTPException(status_code=403, detail="Permessi insufficienti")
    
    # Validate references
    unita = await db.unita.find_one({"id": data.unita_id})
    if not unita:
        raise HTTPException(status_code=404, detail="Unità non trovata")
    
    # Check no active contract on unit
    existing = await db.contratti.find_one({"unita_id": data.unita_id, "stato": "attivo"})
    if existing:
        raise HTTPException(status_code=400, detail="Esiste già un contratto attivo per questa unità")
    
    locatore = await db.soggetti.find_one({"id": data.locatore_id})
    if not locatore:
        raise HTTPException(status_code=404, detail="Locatore non trovato")
    
    affittuario = await db.soggetti.find_one({"id": data.affittuario_id})
    if not affittuario:
        raise HTTPException(status_code=404, detail="Affittuario non trovato")
    
    # Create contratto
    contratto = Contratto(**data.model_dump())
    contratto.data_scadenza = data.data_inizio + relativedelta(months=data.durata_mesi)
    
    if not contratto.reminder_config:
        contratto.reminder_config = ReminderConfig()
    
    contratto_dict = contratto.model_dump()
    # Convert dates to ISO strings
    for key in ["data_firma", "data_inizio", "data_scadenza", "deposito_data", "created_at"]:
        if contratto_dict.get(key):
            contratto_dict[key] = contratto_dict[key].isoformat() if hasattr(contratto_dict[key], 'isoformat') else contratto_dict[key]
    
    await db.contratti.insert_one(contratto_dict)
    
    # Generate rate
    rate = generate_rate(contratto)
    if rate:
        await db.rate.insert_many(rate)
    
    # IMPORTANTE: Aggiorna stato unità a "locata"
    await db.unita.update_one(
        {"id": data.unita_id},
        {"$set": {
            "stato": "locata",
            "contratto_attivo_id": contratto.id,
            "affittuario_nome": affittuario["nome"] if affittuario else None
        }}
    )
    
    await log_audit(db, "contratti", contratto.id, "create", None, contratto_dict, current_user.id)
    
    return contratto


@router.get("/{contratto_id}", response_model=Contratto)
async def get_contratto(
    contratto_id: str,
    current_user: UserInDB = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """Ottieni dettagli contratto."""
    contratto = await db.contratti.find_one({"id": contratto_id}, {"_id": 0})
    if not contratto:
        raise HTTPException(status_code=404, detail="Contratto non trovato")
    
    # Enrich
    unita = await db.unita.find_one({"id": contratto["unita_id"]}, {"_id": 0})
    if unita:
        contratto["unita_codice"] = unita["codice_unita"]
        immobile = await db.immobili.find_one({"id": unita["immobile_id"]}, {"_id": 0})
        contratto["immobile_titolo"] = immobile["titolo"] if immobile else None
    
    locatore = await db.soggetti.find_one({"id": contratto["locatore_id"]}, {"_id": 0})
    contratto["locatore_nome"] = locatore["nome"] if locatore else None
    
    affittuario = await db.soggetti.find_one({"id": contratto["affittuario_id"]}, {"_id": 0})
    contratto["affittuario_nome"] = affittuario["nome"] if affittuario else None
    
    return contratto


@router.put("/{contratto_id}", response_model=Contratto)
async def update_contratto(
    contratto_id: str,
    data: ContrattoUpdate,
    current_user: UserInDB = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """Aggiorna contratto."""
    if current_user.ruolo == UserRole.LETTURA:
        raise HTTPException(status_code=403, detail="Permessi insufficienti")
    
    existing = await db.contratti.find_one({"id": contratto_id}, {"_id": 0})
    if not existing:
        raise HTTPException(status_code=404, detail="Contratto non trovato")
    
    update_dict = data.model_dump(exclude_unset=True)
    
    # Convert dates
    for key in ["data_firma", "data_inizio", "deposito_data"]:
        if key in update_dict and update_dict[key]:
            update_dict[key] = update_dict[key].isoformat()
    
    # Recalculate scadenza if durata changes
    if "durata_mesi" in update_dict:
        data_inizio = date.fromisoformat(existing["data_inizio"])
        update_dict["data_scadenza"] = (data_inizio + relativedelta(months=update_dict["durata_mesi"])).isoformat()
    
    if update_dict:
        await db.contratti.update_one({"id": contratto_id}, {"$set": update_dict})
        await log_audit(db, "contratti", contratto_id, "update", existing, update_dict, current_user.id)
    
    updated = await db.contratti.find_one({"id": contratto_id}, {"_id": 0})
    return updated


@router.post("/{contratto_id}/chiudi")
async def chiudi_contratto(
    contratto_id: str,
    current_user: UserInDB = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """Chiudi contratto e libera l'unità."""
    if current_user.ruolo == UserRole.LETTURA:
        raise HTTPException(status_code=403, detail="Permessi insufficienti")
    
    existing = await db.contratti.find_one({"id": contratto_id}, {"_id": 0})
    if not existing:
        raise HTTPException(status_code=404, detail="Contratto non trovato")
    
    await db.contratti.update_one({"id": contratto_id}, {"$set": {"stato": "chiuso"}})
    
    # Libera l'unità
    await db.unita.update_one(
        {"id": existing["unita_id"]},
        {"$set": {
            "stato": "libera",
            "contratto_attivo_id": None,
            "affittuario_nome": None
        }}
    )
    
    await log_audit(db, "contratti", contratto_id, "update", existing, {"stato": "chiuso"}, current_user.id)
    
    return {"message": "Contratto chiuso"}


@router.get("/{contratto_id}/rate")
async def get_rate_contratto(
    contratto_id: str,
    current_user: UserInDB = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """Ottieni rate del contratto."""
    rate = await db.rate.find({"contratto_id": contratto_id}, {"_id": 0}).sort("periodo", 1).to_list(100)
    return rate
