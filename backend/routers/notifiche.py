"""
Router Notifiche con supporto per Celery tasks e gestione avanzata.
"""

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
        query["stato"] = {"$nin": [StatoNotifica.READ.value, "read"]}
    
    notifiche = await db.notifiche.find(query, {"_id": 0}).sort("created_at", -1).skip(skip).limit(limit).to_list(limit)
    return notifiche


@router.get("/all")
async def list_all_notifiche(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    stato: Optional[str] = None,
    tipo: Optional[str] = None,
    current_user: UserInDB = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """Lista tutte le notifiche (solo supervisori)."""
    if current_user.ruolo != UserRole.SUPERVISORE:
        raise HTTPException(status_code=403, detail="Solo supervisori")
    
    query = {}
    if stato:
        query["stato"] = stato
    if tipo:
        query["tipo"] = tipo
    
    notifiche = await db.notifiche.find(query, {"_id": 0}).sort("created_at", -1).skip(skip).limit(limit).to_list(limit)
    
    # Arricchisci con info utente
    for n in notifiche:
        user = await db.users.find_one({"id": n.get("user_id")}, {"_id": 0, "nome": 1, "email": 1})
        n["user_nome"] = user.get("nome") if user else None
        n["user_email"] = user.get("email") if user else None
    
    return notifiche


@router.get("/count-non-lette")
async def count_non_lette(
    current_user: UserInDB = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """Conta notifiche non lette."""
    count = await db.notifiche.count_documents({
        "user_id": current_user.id,
        "stato": {"$nin": [StatoNotifica.READ.value, "read"]}
    })
    return {"count": count}


@router.get("/stats")
async def get_stats(
    current_user: UserInDB = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """Statistiche notifiche per dashboard."""
    user_query = {"user_id": current_user.id}
    
    total = await db.notifiche.count_documents(user_query)
    pending = await db.notifiche.count_documents({**user_query, "stato": "pending"})
    sent = await db.notifiche.count_documents({**user_query, "stato": "sent"})
    failed = await db.notifiche.count_documents({**user_query, "stato": "failed"})
    read = await db.notifiche.count_documents({**user_query, "stato": "read"})
    
    # Conta per tipo
    by_tipo = {}
    for tipo in ["scadenza_contratto", "rata_ritardo", "doc_scadenza", "evento_critico", "sistema"]:
        by_tipo[tipo] = await db.notifiche.count_documents({**user_query, "tipo": tipo})
    
    return {
        "total": total,
        "by_stato": {
            "pending": pending,
            "sent": sent,
            "failed": failed,
            "read": read
        },
        "by_tipo": by_tipo
    }


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
        {"user_id": current_user.id, "stato": {"$nin": [StatoNotifica.READ.value, "read"]}},
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


@router.post("/trigger-check")
async def trigger_notification_check(
    check_type: str = Query("all", description="Tipo check: rate, contratti, documenti, eventi, all"),
    current_user: UserInDB = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """
    Trigger manuale per controllo notifiche.
    Utile per testing o esecuzione immediata.
    Solo supervisori.
    """
    if current_user.ruolo != UserRole.SUPERVISORE:
        raise HTTPException(status_code=403, detail="Solo supervisori possono triggerare controlli manuali")
    
    try:
        from tasks.notifications import trigger_manual_check
        # Esegui il task in modo asincrono
        result = trigger_manual_check.delay(check_type)
        return {
            "message": f"Check '{check_type}' triggerato",
            "task_id": result.id,
            "status": "queued"
        }
    except Exception as e:
        # Fallback se Celery non è disponibile - esecuzione sincrona
        from tasks.notifications import (
            check_rate_ritardo,
            check_scadenze_contratti,
            check_documenti_scadenza,
            check_eventi_critici
        )
        
        results = []
        if check_type in ["rate", "all"]:
            results.append(check_rate_ritardo())
        if check_type in ["contratti", "all"]:
            results.append(check_scadenze_contratti())
        if check_type in ["documenti", "all"]:
            results.append(check_documenti_scadenza())
        if check_type in ["eventi", "all"]:
            results.append(check_eventi_critici())
        
        return {
            "message": f"Check '{check_type}' eseguito in modo sincrono (Celery non disponibile)",
            "results": results,
            "status": "completed"
        }


@router.post("/retry-failed")
async def retry_failed_notifications(
    current_user: UserInDB = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """
    Riprova l'invio delle notifiche fallite.
    Solo supervisori.
    """
    if current_user.ruolo != UserRole.SUPERVISORE:
        raise HTTPException(status_code=403, detail="Solo supervisori")
    
    try:
        from tasks.notifications import retry_failed_notifications as retry_task
        result = retry_task.delay()
        return {
            "message": "Retry notifiche fallite triggerato",
            "task_id": result.id,
            "status": "queued"
        }
    except Exception as e:
        # Fallback sincrono
        failed = await db.notifiche.find({
            "stato": {"$in": ["pending", "failed"]},
            "tentativi": {"$lt": 3}
        }).to_list(50)
        
        return {
            "message": f"Trovate {len(failed)} notifiche da riprovare (Celery non disponibile)",
            "count": len(failed),
            "status": "info"
        }
