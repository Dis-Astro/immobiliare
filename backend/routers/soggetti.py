from fastapi import APIRouter, HTTPException, Depends, Query
from typing import List, Optional
from motor.motor_asyncio import AsyncIOMotorDatabase

from models.soggetto import Soggetto, SoggettoCreate, SoggettoUpdate, TipoSoggetto
from models.user import UserInDB, UserRole
from routers.auth import get_current_user, get_db
from services.audit import log_audit

router = APIRouter(prefix="/soggetti", tags=["Soggetti"])


@router.get("", response_model=List[Soggetto])
async def list_soggetti(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    tipo: Optional[TipoSoggetto] = None,
    search: Optional[str] = None,
    current_user: UserInDB = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """Lista soggetti con filtri."""
    query = {}
    if tipo:
        query["tipo"] = tipo
    if search:
        query["$or"] = [
            {"nome": {"$regex": search, "$options": "i"}},
            {"cf": {"$regex": search, "$options": "i"}},
            {"piva": {"$regex": search, "$options": "i"}},
            {"email": {"$regex": search, "$options": "i"}}
        ]
    
    soggetti = await db.soggetti.find(query, {"_id": 0}).skip(skip).limit(limit).to_list(limit)
    
    # Enrich with rating and contracts count
    for s in soggetti:
        # Count contracts as tenant
        contratti_count = await db.contratti.count_documents({"affittuario_id": s["id"]})
        s["contratti_count"] = contratti_count
        
        # Get average rating
        valutazioni = await db.valutazioni_affittuari.find(
            {"affittuario_id": s["id"]},
            {"_id": 0, "score_pagamenti": 1, "rating_serieta": 1, "rating_comunicazione": 1, "rating_rispetto_immobile": 1, "rating_vicinato": 1}
        ).to_list(100)
        
        if valutazioni:
            total_score = 0
            count = 0
            for v in valutazioni:
                ratings = [v.get(k) for k in ["rating_serieta", "rating_comunicazione", "rating_rispetto_immobile", "rating_vicinato"] if v.get(k)]
                if ratings:
                    total_score += sum(ratings) / len(ratings)
                    count += 1
            s["rating_medio"] = round(total_score / count, 1) if count > 0 else None
    
    return soggetti


@router.get("/count")
async def count_soggetti(
    tipo: Optional[TipoSoggetto] = None,
    current_user: UserInDB = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """Conta soggetti."""
    query = {}
    if tipo:
        query["tipo"] = tipo
    count = await db.soggetti.count_documents(query)
    return {"count": count}


@router.post("", response_model=Soggetto)
async def create_soggetto(
    data: SoggettoCreate,
    current_user: UserInDB = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """Crea nuovo soggetto."""
    if current_user.ruolo == UserRole.LETTURA:
        raise HTTPException(status_code=403, detail="Permessi insufficienti")
    
    # Check for duplicates
    if data.cf:
        existing = await db.soggetti.find_one({"cf": data.cf})
        if existing:
            raise HTTPException(status_code=400, detail="Codice fiscale già registrato")
    
    if data.piva:
        existing = await db.soggetti.find_one({"piva": data.piva})
        if existing:
            raise HTTPException(status_code=400, detail="Partita IVA già registrata")
    
    soggetto = Soggetto(**data.model_dump())
    soggetto_dict = soggetto.model_dump()
    soggetto_dict["created_at"] = soggetto_dict["created_at"].isoformat()
    
    await db.soggetti.insert_one(soggetto_dict)
    await log_audit(db, "soggetti", soggetto.id, "create", None, soggetto_dict, current_user.id)
    
    return soggetto


@router.get("/{soggetto_id}", response_model=Soggetto)
async def get_soggetto(
    soggetto_id: str,
    current_user: UserInDB = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """Ottieni dettagli soggetto."""
    soggetto = await db.soggetti.find_one({"id": soggetto_id}, {"_id": 0})
    if not soggetto:
        raise HTTPException(status_code=404, detail="Soggetto non trovato")
    
    # Enrich with contracts and rating
    contratti = await db.contratti.find(
        {"$or": [{"affittuario_id": soggetto_id}, {"locatore_id": soggetto_id}]},
        {"_id": 0}
    ).to_list(100)
    soggetto["contratti_count"] = len([c for c in contratti if c.get("affittuario_id") == soggetto_id])
    
    valutazioni = await db.valutazioni_affittuari.find(
        {"affittuario_id": soggetto_id},
        {"_id": 0}
    ).to_list(100)
    
    if valutazioni:
        total_score = 0
        count = 0
        for v in valutazioni:
            ratings = [v.get(k) for k in ["rating_serieta", "rating_comunicazione", "rating_rispetto_immobile", "rating_vicinato"] if v.get(k)]
            if ratings:
                total_score += sum(ratings) / len(ratings)
                count += 1
        soggetto["rating_medio"] = round(total_score / count, 1) if count > 0 else None
    
    return soggetto


@router.put("/{soggetto_id}", response_model=Soggetto)
async def update_soggetto(
    soggetto_id: str,
    data: SoggettoUpdate,
    current_user: UserInDB = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """Aggiorna soggetto."""
    if current_user.ruolo == UserRole.LETTURA:
        raise HTTPException(status_code=403, detail="Permessi insufficienti")
    
    existing = await db.soggetti.find_one({"id": soggetto_id}, {"_id": 0})
    if not existing:
        raise HTTPException(status_code=404, detail="Soggetto non trovato")
    
    update_dict = data.model_dump(exclude_unset=True)
    
    if update_dict:
        await db.soggetti.update_one({"id": soggetto_id}, {"$set": update_dict})
        await log_audit(db, "soggetti", soggetto_id, "update", existing, update_dict, current_user.id)
    
    updated = await db.soggetti.find_one({"id": soggetto_id}, {"_id": 0})
    return updated


@router.delete("/{soggetto_id}")
async def delete_soggetto(
    soggetto_id: str,
    current_user: UserInDB = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """Elimina soggetto (solo se non ha contratti attivi)."""
    if current_user.ruolo == UserRole.LETTURA:
        raise HTTPException(status_code=403, detail="Permessi insufficienti")
    
    # Check for active contracts
    active_contracts = await db.contratti.count_documents({
        "$or": [{"affittuario_id": soggetto_id}, {"locatore_id": soggetto_id}],
        "stato": "attivo"
    })
    
    if active_contracts > 0:
        raise HTTPException(
            status_code=400, 
            detail=f"Impossibile eliminare: {active_contracts} contratti attivi collegati"
        )
    
    existing = await db.soggetti.find_one({"id": soggetto_id}, {"_id": 0})
    if not existing:
        raise HTTPException(status_code=404, detail="Soggetto non trovato")
    
    await db.soggetti.delete_one({"id": soggetto_id})
    await log_audit(db, "soggetti", soggetto_id, "delete", existing, None, current_user.id)
    
    return {"message": "Soggetto eliminato"}
