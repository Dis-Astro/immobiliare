from fastapi import APIRouter, HTTPException, Depends, Query
from typing import List, Optional
from motor.motor_asyncio import AsyncIOMotorDatabase

from models.verbale import VerbaleStato, VerbaleCreate, TipoVerbale
from models.user import UserInDB, UserRole
from routers.auth import get_current_user, get_db
from services.audit import log_audit

router = APIRouter(prefix="/verbali", tags=["Verbali"])


@router.get("", response_model=List[VerbaleStato])
async def list_verbali(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    contratto_id: Optional[str] = None,
    tipo: Optional[TipoVerbale] = None,
    current_user: UserInDB = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """Lista verbali."""
    query = {}
    if contratto_id:
        query["contratto_id"] = contratto_id
    if tipo:
        query["tipo"] = tipo
    
    verbali = await db.verbali.find(query, {"_id": 0}).sort("data", -1).skip(skip).limit(limit).to_list(limit)
    
    # Enrich
    for v in verbali:
        contratto = await db.contratti.find_one({"id": v["contratto_id"]}, {"_id": 0})
        if contratto:
            v["contratto_codice"] = contratto.get("codice_contratto")
            affittuario = await db.soggetti.find_one({"id": contratto["affittuario_id"]}, {"nome": 1})
            v["affittuario_nome"] = affittuario["nome"] if affittuario else None
            
            unita = await db.unita.find_one({"id": contratto["unita_id"]}, {"codice_unita": 1})
            v["unita_codice"] = unita["codice_unita"] if unita else None
    
    return verbali


@router.get("/contratto/{contratto_id}/confronto")
async def confronta_verbali(
    contratto_id: str,
    current_user: UserInDB = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """Confronta verbale consegna vs riconsegna per un contratto."""
    consegna = await db.verbali.find_one(
        {"contratto_id": contratto_id, "tipo": TipoVerbale.CONSEGNA.value},
        {"_id": 0}
    )
    
    riconsegna = await db.verbali.find_one(
        {"contratto_id": contratto_id, "tipo": TipoVerbale.RICONSEGNA.value},
        {"_id": 0}
    )
    
    if not consegna:
        return {"message": "Nessun verbale di consegna trovato", "consegna": None, "riconsegna": riconsegna, "confronto": []}
    
    confronto = []
    if consegna and riconsegna:
        consegna_items = {item["ambiente"]: item for item in consegna.get("checklist", [])}
        riconsegna_items = {item["ambiente"]: item for item in riconsegna.get("checklist", [])}
        
        all_ambienti = set(consegna_items.keys()) | set(riconsegna_items.keys())
        
        for ambiente in all_ambienti:
            c = consegna_items.get(ambiente, {})
            r = riconsegna_items.get(ambiente, {})
            
            stato_consegna = c.get("stato", "N/A")
            stato_riconsegna = r.get("stato", "N/A")
            
            # Determine if degraded
            stato_ordine = {"ottimo": 4, "buono": 3, "usurato": 2, "danneggiato": 1, "N/A": 0}
            degradato = stato_ordine.get(stato_riconsegna, 0) < stato_ordine.get(stato_consegna, 0)
            
            confronto.append({
                "ambiente": ambiente,
                "stato_consegna": stato_consegna,
                "stato_riconsegna": stato_riconsegna,
                "degradato": degradato,
                "note_consegna": c.get("note"),
                "note_riconsegna": r.get("note"),
                "foto_consegna": c.get("foto_refs", []),
                "foto_riconsegna": r.get("foto_refs", [])
            })
    
    return {
        "consegna": consegna,
        "riconsegna": riconsegna,
        "confronto": confronto
    }


@router.post("", response_model=VerbaleStato)
async def create_verbale(
    data: VerbaleCreate,
    current_user: UserInDB = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """Crea verbale consegna/riconsegna."""
    if current_user.ruolo == UserRole.LETTURA:
        raise HTTPException(status_code=403, detail="Permessi insufficienti")
    
    # Check contratto exists
    contratto = await db.contratti.find_one({"id": data.contratto_id})
    if not contratto:
        raise HTTPException(status_code=404, detail="Contratto non trovato")
    
    # Check if verbale of same type already exists
    existing = await db.verbali.find_one({
        "contratto_id": data.contratto_id,
        "tipo": data.tipo
    })
    if existing:
        raise HTTPException(
            status_code=400, 
            detail=f"Verbale di {data.tipo.value} già esistente per questo contratto"
        )
    
    verbale = VerbaleStato(**data.model_dump())
    verbale.compilato_da = current_user.id
    
    verbale_dict = verbale.model_dump()
    verbale_dict["created_at"] = verbale_dict["created_at"].isoformat()
    verbale_dict["data"] = verbale_dict["data"].isoformat()
    
    # Convert checklist items
    verbale_dict["checklist"] = [item.model_dump() if hasattr(item, 'model_dump') else item for item in verbale_dict["checklist"]]
    
    await db.verbali.insert_one(verbale_dict)
    await log_audit(db, "verbali", verbale.id, "create", None, verbale_dict, current_user.id)
    
    return verbale


@router.get("/{verbale_id}", response_model=VerbaleStato)
async def get_verbale(
    verbale_id: str,
    current_user: UserInDB = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """Ottieni dettagli verbale."""
    verbale = await db.verbali.find_one({"id": verbale_id}, {"_id": 0})
    if not verbale:
        raise HTTPException(status_code=404, detail="Verbale non trovato")
    
    # Enrich
    contratto = await db.contratti.find_one({"id": verbale["contratto_id"]}, {"_id": 0})
    if contratto:
        verbale["contratto_codice"] = contratto.get("codice_contratto")
        affittuario = await db.soggetti.find_one({"id": contratto["affittuario_id"]}, {"nome": 1})
        verbale["affittuario_nome"] = affittuario["nome"] if affittuario else None
    
    return verbale


@router.put("/{verbale_id}", response_model=VerbaleStato)
async def update_verbale(
    verbale_id: str,
    data: VerbaleCreate,
    current_user: UserInDB = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """Aggiorna verbale."""
    if current_user.ruolo == UserRole.LETTURA:
        raise HTTPException(status_code=403, detail="Permessi insufficienti")
    
    existing = await db.verbali.find_one({"id": verbale_id}, {"_id": 0})
    if not existing:
        raise HTTPException(status_code=404, detail="Verbale non trovato")
    
    update_dict = data.model_dump()
    update_dict["data"] = update_dict["data"].isoformat()
    update_dict["checklist"] = [item.model_dump() if hasattr(item, 'model_dump') else item for item in update_dict["checklist"]]
    
    await db.verbali.update_one({"id": verbale_id}, {"$set": update_dict})
    await log_audit(db, "verbali", verbale_id, "update", existing, update_dict, current_user.id)
    
    updated = await db.verbali.find_one({"id": verbale_id}, {"_id": 0})
    return updated
