from fastapi import APIRouter, HTTPException, Depends, Query
from typing import List, Optional
from datetime import date, datetime, timezone
from motor.motor_asyncio import AsyncIOMotorDatabase

from models.rata import Rata, RataCreate, RataUpdate, StatoRata, MetodoPagamento
from models.user import UserInDB, UserRole
from routers.auth import get_current_user, get_db
from services.audit import log_audit

router = APIRouter(prefix="/rate", tags=["Rate/Pagamenti"])


@router.get("", response_model=List[Rata])
async def list_rate(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    contratto_id: Optional[str] = None,
    stato: Optional[StatoRata] = None,
    periodo_da: Optional[str] = None,
    periodo_a: Optional[str] = None,
    in_ritardo: Optional[bool] = None,
    current_user: UserInDB = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """Lista rate con filtri."""
    query = {}
    if contratto_id:
        query["contratto_id"] = contratto_id
    if stato:
        query["stato"] = stato
    if periodo_da:
        query["periodo"] = {"$gte": periodo_da}
    if periodo_a:
        if "periodo" not in query:
            query["periodo"] = {}
        query["periodo"]["$lte"] = periodo_a
    if in_ritardo:
        query["stato"] = StatoRata.IN_RITARDO
    
    rate = await db.rate.find(query, {"_id": 0}).sort("data_scadenza", -1).skip(skip).limit(limit).to_list(limit)
    
    # Update ritardo status and enrich
    today = date.today()
    for r in rate:
        # Calculate delay
        if r.get("data_scadenza") and r["stato"] == StatoRata.DA_INCASSARE.value:
            scadenza = date.fromisoformat(r["data_scadenza"]) if isinstance(r["data_scadenza"], str) else r["data_scadenza"]
            if today > scadenza:
                r["giorni_ritardo"] = (today - scadenza).days
                r["stato"] = StatoRata.IN_RITARDO.value
                # Update in DB
                await db.rate.update_one(
                    {"id": r["id"]},
                    {"$set": {"stato": StatoRata.IN_RITARDO.value, "giorni_ritardo": r["giorni_ritardo"]}}
                )
        
        # Enrich with contract/tenant info
        contratto = await db.contratti.find_one({"id": r["contratto_id"]}, {"_id": 0})
        if contratto:
            r["contratto_codice"] = contratto.get("codice_contratto")
            affittuario = await db.soggetti.find_one({"id": contratto["affittuario_id"]}, {"nome": 1})
            r["affittuario_nome"] = affittuario["nome"] if affittuario else None
            
            unita = await db.unita.find_one({"id": contratto["unita_id"]}, {"immobile_id": 1})
            if unita:
                immobile = await db.immobili.find_one({"id": unita["immobile_id"]}, {"titolo": 1})
                r["immobile_titolo"] = immobile["titolo"] if immobile else None
    
    return rate


@router.get("/in-ritardo")
async def get_rate_in_ritardo(
    limit: int = Query(20, ge=1, le=100),
    current_user: UserInDB = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """Ottieni rate in ritardo ordinate per gravità."""
    today = date.today().isoformat()
    
    rate = await db.rate.find({
        "stato": {"$in": [StatoRata.DA_INCASSARE.value, StatoRata.IN_RITARDO.value]},
        "data_scadenza": {"$lt": today}
    }, {"_id": 0}).sort("data_scadenza", 1).limit(limit).to_list(limit)
    
    # Enrich
    for r in rate:
        scadenza = date.fromisoformat(r["data_scadenza"]) if isinstance(r["data_scadenza"], str) else r["data_scadenza"]
        r["giorni_ritardo"] = (date.today() - scadenza).days
        
        contratto = await db.contratti.find_one({"id": r["contratto_id"]}, {"_id": 0})
        if contratto:
            r["contratto_codice"] = contratto.get("codice_contratto")
            affittuario = await db.soggetti.find_one({"id": contratto["affittuario_id"]}, {"nome": 1})
            r["affittuario_nome"] = affittuario["nome"] if affittuario else None
            
            unita = await db.unita.find_one({"id": contratto["unita_id"]}, {"immobile_id": 1})
            if unita:
                immobile = await db.immobili.find_one({"id": unita["immobile_id"]}, {"titolo": 1})
                r["immobile_titolo"] = immobile["titolo"] if immobile else None
    
    return rate


@router.get("/stats")
async def get_rate_stats(
    periodo: Optional[str] = None,  # YYYY-MM
    current_user: UserInDB = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """Statistiche rate."""
    query = {}
    if periodo:
        query["periodo"] = periodo
    else:
        # Current month
        query["periodo"] = date.today().strftime("%Y-%m")
    
    rate = await db.rate.find(query, {"_id": 0}).to_list(1000)
    
    totale = sum(r["importo"] for r in rate)
    incassato = sum(r["importo"] for r in rate if r["stato"] == StatoRata.INCASSATO.value)
    in_ritardo = sum(r["importo"] for r in rate if r["stato"] == StatoRata.IN_RITARDO.value)
    da_incassare = sum(r["importo"] for r in rate if r["stato"] == StatoRata.DA_INCASSARE.value)
    
    return {
        "periodo": query["periodo"],
        "totale": totale,
        "incassato": incassato,
        "in_ritardo": in_ritardo,
        "da_incassare": da_incassare,
        "percentuale_incassato": round(incassato / totale * 100, 1) if totale > 0 else 0
    }


@router.put("/{rata_id}", response_model=Rata)
async def update_rata(
    rata_id: str,
    data: RataUpdate,
    current_user: UserInDB = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """Aggiorna rata (es. segna come incassata)."""
    if current_user.ruolo == UserRole.LETTURA:
        raise HTTPException(status_code=403, detail="Permessi insufficienti")
    
    existing = await db.rate.find_one({"id": rata_id}, {"_id": 0})
    if not existing:
        raise HTTPException(status_code=404, detail="Rata non trovata")
    
    update_dict = data.model_dump(exclude_unset=True)
    
    # Auto-set incasso date if marking as paid
    if update_dict.get("stato") == StatoRata.INCASSATO and "data_incasso" not in update_dict:
        update_dict["data_incasso"] = date.today().isoformat()
    
    # Convert dates
    if "data_incasso" in update_dict and update_dict["data_incasso"]:
        update_dict["data_incasso"] = update_dict["data_incasso"].isoformat() if hasattr(update_dict["data_incasso"], 'isoformat') else update_dict["data_incasso"]
    
    if update_dict:
        await db.rate.update_one({"id": rata_id}, {"$set": update_dict})
        await log_audit(db, "rate", rata_id, "update", existing, update_dict, current_user.id)
    
    updated = await db.rate.find_one({"id": rata_id}, {"_id": 0})
    return updated


@router.post("/{rata_id}/incassa")
async def incassa_rata(
    rata_id: str,
    metodo: MetodoPagamento = MetodoPagamento.BONIFICO,
    riferimento: Optional[str] = None,
    current_user: UserInDB = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """Azione rapida: segna rata come incassata."""
    if current_user.ruolo == UserRole.LETTURA:
        raise HTTPException(status_code=403, detail="Permessi insufficienti")
    
    existing = await db.rate.find_one({"id": rata_id}, {"_id": 0})
    if not existing:
        raise HTTPException(status_code=404, detail="Rata non trovata")
    
    update_dict = {
        "stato": StatoRata.INCASSATO.value,
        "data_incasso": date.today().isoformat(),
        "metodo": metodo.value,
        "riferimento": riferimento
    }
    
    await db.rate.update_one({"id": rata_id}, {"$set": update_dict})
    await log_audit(db, "rate", rata_id, "update", existing, update_dict, current_user.id)
    
    return {"message": "Rata incassata", "data_incasso": update_dict["data_incasso"]}
