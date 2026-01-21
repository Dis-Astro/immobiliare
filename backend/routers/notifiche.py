from fastapi import APIRouter, HTTPException, Depends, Query
from typing import List, Optional
from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorDatabase

from models.notifica import Notifica, NotificaCreate, TipoNotifica, StatoNotifica
from models.user import UserInDB, UserRole
from routers.auth import get_current_user, get_db

router = APIRouter(prefix="/notifiche", tags=["Notifiche"])


@router.get("", response_model=List[Notifica])
async def list_notifiche(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    stato: Optional[StatoNotifica] = None,
    tipo: Optional[TipoNotifica] = None,
    non_lette: bool = False,
    current_user: UserInDB = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """Lista notifiche per utente corrente."""
    query = {"user_id": current_user.id}
    if stato:
        query["stato"] = stato
    if tipo:
        query["tipo"] = tipo
    if non_lette:
        query["stato"] = {"$ne": StatoNotifica.READ.value}
    
    notifiche = await db.notifiche.find(query, {"_id": 0}).sort("created_at", -1).skip(skip).limit(limit).to_list(limit)
    return notifiche


@router.get("/count-non-lette")
async def count_non_lette(
    current_user: UserInDB = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """Conta notifiche non lette."""
    count = await db.notifiche.count_documents({
        "user_id": current_user.id,
        "stato": {"$ne": StatoNotifica.READ.value}
    })
    return {"count": count}


@router.post("/{notifica_id}/read")
async def mark_as_read(
    notifica_id: str,
    current_user: UserInDB = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """Segna notifica come letta."""
    result = await db.notifiche.update_one(
        {"id": notifica_id, "user_id": current_user.id},
        {"$set": {
            "stato": StatoNotifica.READ.value,
            "read_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Notifica non trovata")
    
    return {"message": "Notifica segnata come letta"}


@router.post("/read-all")
async def mark_all_as_read(
    current_user: UserInDB = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """Segna tutte le notifiche come lette."""
    result = await db.notifiche.update_many(
        {"user_id": current_user.id, "stato": {"$ne": StatoNotifica.READ.value}},
        {"$set": {
            "stato": StatoNotifica.READ.value,
            "read_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    return {"message": f"{result.modified_count} notifiche segnate come lette"}


@router.delete("/{notifica_id}")
async def delete_notifica(
    notifica_id: str,
    current_user: UserInDB = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """Elimina notifica."""
    result = await db.notifiche.delete_one({
        "id": notifica_id,
        "user_id": current_user.id
    })
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Notifica non trovata")
    
    return {"message": "Notifica eliminata"}
