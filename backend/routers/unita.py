from fastapi import APIRouter, HTTPException, Depends, Query
from typing import List, Optional
from motor.motor_asyncio import AsyncIOMotorDatabase

from models.unita import Unita, UnitaCreate, UnitaUpdate, TipoImmobile, DestinazioneUso
from models.user import UserInDB, UserRole
from routers.auth import get_current_user, get_db
from services.audit import log_audit

router = APIRouter(prefix="/unita", tags=["Unità"])


@router.get("", response_model=List[Unita])
async def list_unita(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    immobile_id: Optional[str] = None,
    tipo_immobile: Optional[TipoImmobile] = None,
    stato: Optional[str] = None,
    search: Optional[str] = None,
    current_user: UserInDB = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """Lista unità con filtri."""
    query = {}
    if immobile_id:
        query["immobile_id"] = immobile_id
    if tipo_immobile:
        query["tipo_immobile"] = tipo_immobile
    if search:
        query["$or"] = [
            {"codice_unita": {"$regex": search, "$options": "i"}},
            {"note": {"$regex": search, "$options": "i"}}
        ]
    
    unita_list = await db.unita.find(query, {"_id": 0}).skip(skip).limit(limit).to_list(limit)
    
    # Enrich with contract info and state
    for u in unita_list:
        contratto = await db.contratti.find_one(
            {"unita_id": u["id"], "stato": "attivo"},
            {"_id": 0, "id": 1, "affittuario_id": 1}
        )
        if contratto:
            u["contratto_attivo_id"] = contratto["id"]
            affittuario = await db.soggetti.find_one({"id": contratto["affittuario_id"]}, {"nome": 1})
            u["affittuario_nome"] = affittuario["nome"] if affittuario else None
            u["stato"] = "locata"
        else:
            # Check if in maintenance
            intervento = await db.interventi.find_one(
                {"unita_id": u["id"], "stato": {"$in": ["richiesto", "pianificato", "in_corso"]}},
                {"_id": 0}
            )
            u["stato"] = "in_manutenzione" if intervento else "libera"
    
    # Filter by stato if requested
    if stato:
        unita_list = [u for u in unita_list if u.get("stato") == stato]
    
    return unita_list


@router.get("/count")
async def count_unita(
    immobile_id: Optional[str] = None,
    stato: Optional[str] = None,
    current_user: UserInDB = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """Conta unità."""
    query = {}
    if immobile_id:
        query["immobile_id"] = immobile_id
    
    count = await db.unita.count_documents(query)
    
    # Count by stato if needed
    if stato:
        unita_list = await db.unita.find(query, {"_id": 0, "id": 1}).to_list(1000)
        filtered = []
        for u in unita_list:
            contratto = await db.contratti.find_one({"unita_id": u["id"], "stato": "attivo"})
            u_stato = "locata" if contratto else "libera"
            if u_stato == stato:
                filtered.append(u)
        count = len(filtered)
    
    return {"count": count}


@router.post("", response_model=Unita)
async def create_unita(
    data: UnitaCreate,
    current_user: UserInDB = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """Crea nuova unità."""
    if current_user.ruolo == UserRole.LETTURA:
        raise HTTPException(status_code=403, detail="Permessi insufficienti")
    
    # Check immobile exists
    immobile = await db.immobili.find_one({"id": data.immobile_id})
    if not immobile:
        raise HTTPException(status_code=404, detail="Immobile non trovato")
    
    # Check codice unique within immobile
    existing = await db.unita.find_one({
        "immobile_id": data.immobile_id,
        "codice_unita": data.codice_unita
    })
    if existing:
        raise HTTPException(status_code=400, detail="Codice unità già esistente per questo immobile")
    
    unita = Unita(**data.model_dump())
    unita_dict = unita.model_dump()
    unita_dict["created_at"] = unita_dict["created_at"].isoformat()
    
    await db.unita.insert_one(unita_dict)
    await log_audit(db, "unita", unita.id, "create", None, unita_dict, current_user.id)
    
    return unita


@router.get("/{unita_id}", response_model=Unita)
async def get_unita(
    unita_id: str,
    current_user: UserInDB = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """Ottieni dettagli unità."""
    unita = await db.unita.find_one({"id": unita_id}, {"_id": 0})
    if not unita:
        raise HTTPException(status_code=404, detail="Unità non trovata")
    
    # Enrich
    contratto = await db.contratti.find_one(
        {"unita_id": unita_id, "stato": "attivo"},
        {"_id": 0}
    )
    if contratto:
        unita["contratto_attivo_id"] = contratto["id"]
        affittuario = await db.soggetti.find_one({"id": contratto["affittuario_id"]}, {"nome": 1})
        unita["affittuario_nome"] = affittuario["nome"] if affittuario else None
        unita["stato"] = "locata"
    else:
        unita["stato"] = "libera"
    
    return unita


@router.put("/{unita_id}", response_model=Unita)
async def update_unita(
    unita_id: str,
    data: UnitaUpdate,
    current_user: UserInDB = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """Aggiorna unità."""
    if current_user.ruolo == UserRole.LETTURA:
        raise HTTPException(status_code=403, detail="Permessi insufficienti")
    
    existing = await db.unita.find_one({"id": unita_id}, {"_id": 0})
    if not existing:
        raise HTTPException(status_code=404, detail="Unità non trovata")
    
    update_dict = data.model_dump(exclude_unset=True)
    
    if update_dict:
        await db.unita.update_one({"id": unita_id}, {"$set": update_dict})
        await log_audit(db, "unita", unita_id, "update", existing, update_dict, current_user.id)
    
    updated = await db.unita.find_one({"id": unita_id}, {"_id": 0})
    return updated


@router.delete("/{unita_id}")
async def delete_unita(
    unita_id: str,
    current_user: UserInDB = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """Elimina unità (solo se senza contratti)."""
    if current_user.ruolo != UserRole.SUPERVISORE:
        raise HTTPException(status_code=403, detail="Solo supervisore può eliminare unità")
    
    contratti_count = await db.contratti.count_documents({"unita_id": unita_id})
    if contratti_count > 0:
        raise HTTPException(
            status_code=400,
            detail=f"Impossibile eliminare: {contratti_count} contratti collegati"
        )
    
    existing = await db.unita.find_one({"id": unita_id}, {"_id": 0})
    if not existing:
        raise HTTPException(status_code=404, detail="Unità non trovata")
    
    await db.unita.delete_one({"id": unita_id})
    await log_audit(db, "unita", unita_id, "delete", existing, None, current_user.id)
    
    return {"message": "Unità eliminata"}


@router.get("/tipi/lista")
async def get_tipi_immobile():
    """Ottieni lista tipi immobile."""
    return [{"value": t.value, "label": t.value.replace("_", " ").title()} for t in TipoImmobile]


@router.get("/destinazioni/lista")
async def get_destinazioni_uso():
    """Ottieni lista destinazioni d'uso."""
    return [{"value": d.value, "label": d.value.replace("_", " ").title()} for d in DestinazioneUso]
