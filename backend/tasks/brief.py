"""
Celery task: invio brief mattutino AI via email.
Eseguito ogni ora; verifica al volo se l'orario corrisponde alla configurazione.
"""
import asyncio
import logging
import os
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from motor.motor_asyncio import AsyncIOMotorClient

from celery_app import celery_app
from services.brief import get_brief_config, build_brief, BRIEF_CONFIG_KEY
from utils.email import send_email

logger = logging.getLogger(__name__)

MONGO_URL = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
DB_NAME = os.environ.get('DB_NAME', 'test_database')
TZ = ZoneInfo("Europe/Rome")


async def _run_brief_async(force: bool = False) -> dict:
    """Logica async del task: legge config, costruisce e invia il brief."""
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]
    try:
        config = await get_brief_config(db)

        if not force:
            if not config.get("enabled"):
                return {"skipped": "disabled"}

            now = datetime.now(TZ)
            cfg_hour = config.get("cron_hour", 8)
            cfg_minute = config.get("cron_minute", 0)
            if now.hour != cfg_hour or now.minute != cfg_minute:
                return {"skipped": f"time {now.hour:02d}:{now.minute:02d} != {cfg_hour:02d}:{cfg_minute:02d}"}

            # Idempotenza: non inviare due volte nello stesso giorno
            today = now.date().isoformat()
            last_sent = config.get("last_sent_at")
            if last_sent and last_sent.startswith(today) and config.get("last_status") in ("success", "partial"):
                return {"skipped": "already sent today"}

        recipients = config.get("recipients", []) or []
        if not recipients:
            return {"skipped": "no recipients"}

        brief = await build_brief(db, config)
        subject = f"☀️ Brief EstateWise — {brief['data']['data_brief']}"

        sent = 0
        errors = []
        for email_addr in recipients:
            try:
                ok = await send_email(
                    to_email=email_addr,
                    subject=subject,
                    body_html=brief["html"],
                    body_text=brief["text"],
                )
                if ok:
                    sent += 1
                else:
                    errors.append(f"{email_addr}: SMTP non configurato")
            except Exception as e:
                errors.append(f"{email_addr}: {e}")

        status = "success" if sent and not errors else ("partial" if sent else "error")
        await db.config.update_one(
            {"key": BRIEF_CONFIG_KEY},
            {"$set": {
                "last_sent_at": datetime.now(timezone.utc).isoformat(),
                "last_status": status,
                "last_error": "; ".join(errors) if errors else None,
            }, "$setOnInsert": {"key": BRIEF_CONFIG_KEY}},
            upsert=True
        )

        return {
            "sent": sent,
            "total": len(recipients),
            "status": status,
            "errors": errors,
            "stats": brief["stats"]
        }
    finally:
        client.close()


@celery_app.task(name='tasks.brief.send_morning_brief')
def send_morning_brief(force: bool = False) -> dict:
    """Task Celery: invia il brief mattutino se l'ora corrisponde alla config (o force=True)."""
    try:
        return asyncio.run(_run_brief_async(force=force))
    except Exception as e:
        logger.error(f"send_morning_brief failed: {e}", exc_info=True)
        return {"error": str(e)}
