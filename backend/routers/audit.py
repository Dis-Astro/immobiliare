from fastapi import APIRouter, HTTPException, Depends, Query
from typing import List, Optional
from motor.motor_asyncio import AsyncIOMotorDatabase

from models.audit import AuditLog
from models.user import UserInDB, UserRole
from routers.auth import get_current_user, get_db

router = APIRouter(prefix="/audit", tags=["Audit Log"])


@router.get("", response_model=List[AuditLog])
async def list_audit_logs(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    tabella: Optional[str] = None,
    azione: Optional[str] = None,
    user_id: Optional[str] = None,
    current_user: UserInDB = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """Lista audit log (solo supervisore)."""
    if current_user.ruolo != UserRole.SUPERVISORE:
        raise HTTPException(status_code=403, detail="Solo supervisori possono accedere ai log di audit")
    
    query = {}
    if tabella:
        query["tabella"] = tabella
    if azione:
        query["azione"] = azione
    if user_id:
        query["user_id"] = user_id
    
    logs = await db.audit_log.find(query, {"_id": 0}).sort("timestamp", -1).skip(skip).limit(limit).to_list(limit)
    
    from bson import ObjectId
    def _clean(v):
        if isinstance(v, ObjectId):
            return str(v)
        if isinstance(v, dict):
            return {k: _clean(val) for k, val in v.items() if k != "_id"}
        if isinstance(v, list):
            return [_clean(x) for x in v]
        return v
    
    # Enrich with user name & sanitize embedded ObjectIds in old_values/new_values
    for log in logs:
        if log.get("user_id"):
            user = await db.users.find_one({"id": log["user_id"]}, {"_id": 0, "nome": 1})
            log["user_nome"] = user["nome"] if user else None
        for key in ("old_values", "new_values"):
            if log.get(key) is not None:
                log[key] = _clean(log[key])
    
    return logs


@router.get("/count")
async def count_audit_logs(
    tabella: Optional[str] = None,
    current_user: UserInDB = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """Conta audit log."""
    if current_user.ruolo != UserRole.SUPERVISORE:
        raise HTTPException(status_code=403, detail="Solo supervisori possono accedere ai log di audit")
    
    query = {}
    if tabella:
        query["tabella"] = tabella
    
    count = await db.audit_log.count_documents(query)
    return {"count": count}
