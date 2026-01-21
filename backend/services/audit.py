from datetime import datetime, timezone
from typing import Optional, Dict, Any
from motor.motor_asyncio import AsyncIOMotorDatabase
import uuid


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
    """Log an audit entry."""
    audit_entry = {
        "id": str(uuid.uuid4()),
        "tabella": tabella,
        "record_id": record_id,
        "azione": azione,
        "old_values": old_values,
        "new_values": new_values,
        "user_id": user_id,
        "ip_address": ip_address,
        "user_agent": user_agent,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    
    await db.audit_log.insert_one(audit_entry)
