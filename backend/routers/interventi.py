from fastapi import APIRouter, HTTPException, Depends, Query
from typing import List, Optional
from motor.motor_asyncio import AsyncIOMotorDatabase

from models.intervento import InterventoManutenzione, InterventoCreate, PrioritaIntervento, StatoIntervento
from models.user import UserInDB, UserRole
from routers.auth import get_current_user, get_db
from services.audit import log_audit

router = APIRouter(prefix="/interventi", tags=["Interventi Manutenzione"])


@router.get("", response_model=List[InterventoManutenzione])
async def list_interventi(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    immobile_id: Optional[str] = None,
    unita_id: Optional[str] = None,
    priorita: Optional[PrioritaIntervento] = None,
    stato: Optional[StatoIntervento] = None,
    current_user: UserInDB = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """Lista interventi manutenzione."""
    query = {}
    if immobile_id:
        query["immobile_id"] = immobile_id
    if unita_id:
        query["unita_id"] = unita_id
    if priorita:
        query["priorita"] = priorita
    if stato:
        query["stato"] = stato
    
    interventi = await db.interventi.find(query, {"_id": 0}).sort("data_richiesta", -1).skip(skip).limit(limit).to_list(limit)
    
    # Enrich
    for i in interventi:
        immobile = await db.immobili.find_one({"id": i["immobile_id"]}, {"titolo": 1})
        i["immobile_titolo"] = immobile["titolo"] if immobile else None
        
        if i.get("unita_id"):
            unita = await db.unita.find_one({"id": i["unita_id"]}, {"codice_unita": 1})
            i["unita_codice"] = unita["codice_unita"] if unita else None
    
    return interventi


@router.post("", response_model=InterventoManutenzione)
async def create_intervento(
    data: InterventoCreate,
    current_user: UserInDB = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """Crea richiesta intervento."""
    if current_user.ruolo == UserRole.LETTURA:
        raise HTTPException(status_code=403, detail="Permessi insufficienti")
    
    intervento = InterventoManutenzione(**data.model_dump())
    intervento.created_by = current_user.id
    
    int_dict = intervento.model_dump()
    int_dict["created_at"] = int_dict["created_at"].isoformat()
    int_dict["data_richiesta"] = int_dict["data_richiesta"].isoformat()
    if int_dict.get("data_pianificata"):
        int_dict["data_pianificata"] = int_dict["data_pianificata"].isoformat()
    if int_dict.get("data_completamento"):
        int_dict["data_completamento"] = int_dict["data_completamento"].isoformat()
    
    await db.interventi.insert_one(int_dict)
    await log_audit(db, "interventi", intervento.id, "create", None, int_dict, current_user.id)
    
    return intervento


@router.get("/{intervento_id}", response_model=InterventoManutenzione)
async def get_intervento(
    intervento_id: str,
    current_user: UserInDB = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """Ottieni dettagli intervento."""
    intervento = await db.interventi.find_one({"id": intervento_id}, {"_id": 0})
    if not intervento:
        raise HTTPException(status_code=404, detail="Intervento non trovato")
    return intervento


@router.put("/{intervento_id}", response_model=InterventoManutenzione)
async def update_intervento(
    intervento_id: str,
    data: InterventoCreate,
    current_user: UserInDB = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """Aggiorna intervento."""
    if current_user.ruolo == UserRole.LETTURA:
        raise HTTPException(status_code=403, detail="Permessi insufficienti")
    
    existing = await db.interventi.find_one({"id": intervento_id}, {"_id": 0})
    if not existing:
        raise HTTPException(status_code=404, detail="Intervento non trovato")
    
    update_dict = data.model_dump()
    update_dict["data_richiesta"] = update_dict["data_richiesta"].isoformat()
    if update_dict.get("data_pianificata"):
        update_dict["data_pianificata"] = update_dict["data_pianificata"].isoformat()
    if update_dict.get("data_completamento"):
        update_dict["data_completamento"] = update_dict["data_completamento"].isoformat()
    
    await db.interventi.update_one({"id": intervento_id}, {"$set": update_dict})
    await log_audit(db, "interventi", intervento_id, "update", existing, update_dict, current_user.id)
    
    updated = await db.interventi.find_one({"id": intervento_id}, {"_id": 0})
    return updated


@router.post("/{intervento_id}/stato")
async def cambia_stato_intervento(
    intervento_id: str,
    nuovo_stato: StatoIntervento,
    current_user: UserInDB = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """Cambia stato intervento."""
    if current_user.ruolo == UserRole.LETTURA:
        raise HTTPException(status_code=403, detail="Permessi insufficienti")
    
    existing = await db.interventi.find_one({"id": intervento_id}, {"_id": 0})
    if not existing:
        raise HTTPException(status_code=404, detail="Intervento non trovato")
    
    update_dict = {"stato": nuovo_stato.value}
    
    # Auto-set dates
    from datetime import date
    if nuovo_stato == StatoIntervento.COMPLETATO:
        update_dict["data_completamento"] = date.today().isoformat()
    
    await db.interventi.update_one({"id": intervento_id}, {"$set": update_dict})
    await log_audit(db, "interventi", intervento_id, "update", existing, update_dict, current_user.id)
    
    return {"message": f"Stato aggiornato a {nuovo_stato.value}"}
