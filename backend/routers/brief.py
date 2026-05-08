"""
Router Brief AI mattutino: configurazione, anteprima, invio manuale.
"""
from fastapi import APIRouter, HTTPException, Depends
from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorDatabase

from models.brief import BriefConfig, BriefConfigUpdate, BriefPreview
from models.user import UserInDB, UserRole
from routers.auth import get_current_user, get_db
from services.brief import get_brief_config, build_brief, BRIEF_CONFIG_KEY
from utils.email import send_email

router = APIRouter(prefix="/brief", tags=["Brief AI"])


@router.get("/config", response_model=BriefConfig)
async def get_config(
    current_user: UserInDB = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """Recupera la configurazione del brief mattutino."""
    config = await get_brief_config(db)
    config.pop("key", None)
    return config


@router.put("/config", response_model=BriefConfig)
async def update_config(
    data: BriefConfigUpdate,
    current_user: UserInDB = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """Aggiorna la configurazione del brief mattutino (solo supervisore)."""
    if current_user.ruolo != UserRole.SUPERVISORE:
        raise HTTPException(status_code=403, detail="Solo supervisori possono modificare la configurazione")

    update_dict = data.model_dump(exclude_unset=True, exclude_none=False)
    if "recipients" in update_dict and update_dict["recipients"] is not None:
        update_dict["recipients"] = [str(r) for r in update_dict["recipients"]]

    update_dict = {k: v for k, v in update_dict.items() if v is not None}

    if update_dict:
        await db.config.update_one(
            {"key": BRIEF_CONFIG_KEY},
            {"$set": update_dict, "$setOnInsert": {"key": BRIEF_CONFIG_KEY}},
            upsert=True
        )

    config = await get_brief_config(db)
    config.pop("key", None)
    return config


@router.post("/preview", response_model=BriefPreview)
async def preview_brief(
    current_user: UserInDB = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """Genera un'anteprima del brief con i dati attuali (non invia email)."""
    config = await get_brief_config(db)
    brief = await build_brief(db, config)
    return BriefPreview(
        summary_html=brief["html"],
        summary_text=brief["text"],
        stats=brief["stats"]
    )


@router.post("/send-now")
async def send_now(
    current_user: UserInDB = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """Invia il brief immediatamente ai destinatari configurati (solo supervisore)."""
    if current_user.ruolo != UserRole.SUPERVISORE:
        raise HTTPException(status_code=403, detail="Solo supervisori possono inviare il brief")

    config = await get_brief_config(db)
    recipients = config.get("recipients", []) or []
    if not recipients:
        raise HTTPException(status_code=400, detail="Nessun destinatario configurato")

    brief = await build_brief(db, config)
    subject = f"☀️ Brief EstateWise — {brief['data']['data_brief']}"

    sent_count = 0
    errors = []
    for email_addr in recipients:
        try:
            ok = await send_email(
                to_email=email_addr,
                subject=subject,
                body_html=brief["html"],
                body_text=brief["text"]
            )
            if ok:
                sent_count += 1
            else:
                errors.append(f"{email_addr}: SMTP non configurato o invio fallito")
        except Exception as e:
            errors.append(f"{email_addr}: {str(e)}")

    status = "success" if sent_count > 0 and not errors else ("partial" if sent_count > 0 else "error")
    last_error = "; ".join(errors) if errors else None

    await db.config.update_one(
        {"key": BRIEF_CONFIG_KEY},
        {"$set": {
            "last_sent_at": datetime.now(timezone.utc).isoformat(),
            "last_status": status,
            "last_error": last_error,
        }, "$setOnInsert": {"key": BRIEF_CONFIG_KEY}},
        upsert=True
    )

    return {
        "sent_count": sent_count,
        "total_recipients": len(recipients),
        "status": status,
        "errors": errors,
        "stats": brief["stats"]
    }
