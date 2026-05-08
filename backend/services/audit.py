from datetime import datetime, timezone
from typing import Optional, Dict, Any
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId
import uuid


def _sanitize(value: Any) -> Any:
    """Strip _id keys and stringify ObjectId/datetime so audit values stay JSON-serializable."""
    if isinstance(value, dict):
        return {k: _sanitize(v) for k, v in value.items() if k != "_id"}
    if isinstance(value, list):
        return [_sanitize(v) for v in value]
    if isinstance(value, ObjectId):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    return value


async def log_audit(
    db: AsyncIOMotorDatabase,
    tabella: str,
    record_id: str,
    azione: str,
    old_values: Optional[Dict[str, Any]],
    new_values: Optional[Dict[str, Any]],
    user_id: Optional[str] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None
):
    """Log an audit entry. Values are sanitized to remove ObjectId/_id and serialize datetimes."""
    audit_entry = {
        "id": str(uuid.uuid4()),
        "tabella": tabella,
        "record_id": record_id,
        "azione": azione,
        "old_values": _sanitize(old_values) if old_values else None,
        "new_values": _sanitize(new_values) if new_values else None,
        "user_id": user_id,
        "ip_address": ip_address,
        "user_agent": user_agent,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    
    await db.audit_log.insert_one(audit_entry)
