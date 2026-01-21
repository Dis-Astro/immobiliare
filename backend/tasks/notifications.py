from celery_app import celery_app
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import date, datetime, timezone
from dateutil.relativedelta import relativedelta
import asyncio
import os
import logging

logger = logging.getLogger(__name__)

# MongoDB connection for tasks
MONGO_URL = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
DB_NAME = os.environ.get('DB_NAME', 'estatewise')


def get_db():
    client = AsyncIOMotorClient(MONGO_URL)
    return client[DB_NAME]


async def create_notification_async(db, tipo, user_id, titolo, messaggio, payload, destinatario_email=None):
    """Create notification and optionally send email."""
    import uuid
    
    # Check for duplicate (same type, user, payload within last 24h)
    existing = await db.notifiche.find_one({
        "tipo": tipo,
        "user_id": user_id,
        "payload_json": payload,
        "created_at": {"$gte": (datetime.now(timezone.utc) - relativedelta(hours=24)).isoformat()}
    })
    
    if existing:
        logger.info(f"Duplicate notification skipped: {tipo} for user {user_id}")
        return None
    
    notifica = {
        "id": str(uuid.uuid4()),
        "tipo": tipo,
        "user_id": user_id,
        "titolo": titolo,
        "messaggio": messaggio,
        "payload_json": payload,
        "destinatario_email": destinatario_email,
        "stato": "pending",
        "tentativi": 0,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.notifiche.insert_one(notifica)
    
    # Send email if configured
    if destinatario_email:
        from utils.email import send_email
        try:
            html = f"""
            <html><body>
            <h2>{titolo}</h2>
            <p>{messaggio}</p>
            <hr>
            <p style="color:#666;font-size:12px;">EstateWise - Gestione Immobili</p>
            </body></html>
            """
            success = await send_email(destinatario_email, titolo, html)
            if success:
                await db.notifiche.update_one(
                    {"id": notifica["id"]},
                    {"$set": {"stato": "sent", "sent_at": datetime.now(timezone.utc).isoformat()}}
                )
            else:
                await db.notifiche.update_one(
                    {"id": notifica["id"]},
                    {"$set": {"stato": "failed", "tentativi": 1, "last_error": "Email send failed"}}
                )
        except Exception as e:
            await db.notifiche.update_one(
                {"id": notifica["id"]},
                {"$set": {"stato": "failed", "tentativi": 1, "last_error": str(e)}}
            )
    
    return notifica


@celery_app.task(name='tasks.notifications.check_scadenze_contratti')
def check_scadenze_contratti():
    """Check expiring contracts: 365, 30, 1 days before."""
    async def run():
        db = get_db()
        today = date.today()
        reminder_days = [365, 30, 1]
        
        for days in reminder_days:
            target_date = (today + relativedelta(days=days)).isoformat()
            
            contratti = await db.contratti.find({
                "stato": "attivo",
                "data_scadenza": target_date
            }, {"_id": 0}).to_list(100)
            
            for contratto in contratti:
                affittuario = await db.soggetti.find_one({"id": contratto["affittuario_id"]})
                unita = await db.unita.find_one({"id": contratto["unita_id"]})
                immobile = await db.immobili.find_one({"id": unita["immobile_id"]}) if unita else None
                
                users = await db.users.find(
                    {"ruolo": {"$in": ["supervisore", "gestore"]}, "attivo": True},
                    {"_id": 0}
                ).to_list(100)
                
                for user in users:
                    await create_notification_async(
                        db,
                        tipo="scadenza_contratto",
                        user_id=user["id"],
                        titolo=f"Contratto {contratto['codice_contratto']} scade tra {days} giorni",
                        messaggio=f"Il contratto con {affittuario['nome'] if affittuario else 'N/A'} per {immobile['titolo'] if immobile else 'N/A'} scadrà il {contratto['data_scadenza']}",
                        payload={
                            "contratto_id": contratto["id"],
                            "giorni_rimanenti": days,
                            "tipo_reminder": "scadenza_contratto"
                        },
                        destinatario_email=user.get("email")
                    )
        
        logger.info(f"Checked contract expirations for {len(reminder_days)} thresholds")
    
    asyncio.get_event_loop().run_until_complete(run())
    return "Contract expiration check completed"


@celery_app.task(name='tasks.notifications.check_rate_ritardo')
def check_rate_ritardo():
    """Check late payments: 1, 7, 15 days after due date."""
    async def run():
        db = get_db()
        today = date.today()
        thresholds = [1, 7, 15]
        
        # Find all unpaid rates with past due date
        rate_scadute = await db.rate.find({
            "stato": {"$in": ["da_incassare", "in_ritardo"]},
            "data_scadenza": {"$lt": today.isoformat()}
        }, {"_id": 0}).to_list(1000)
        
        for rata in rate_scadute:
            scadenza = date.fromisoformat(rata["data_scadenza"])
            giorni_ritardo = (today - scadenza).days
            
            # Update status to in_ritardo
            await db.rate.update_one(
                {"id": rata["id"]},
                {"$set": {"stato": "in_ritardo", "giorni_ritardo": giorni_ritardo}}
            )
            
            # Check if at threshold
            for threshold in thresholds:
                if giorni_ritardo == threshold:
                    contratto = await db.contratti.find_one({"id": rata["contratto_id"]})
                    if not contratto:
                        continue
                    
                    affittuario = await db.soggetti.find_one({"id": contratto["affittuario_id"]})
                    unita = await db.unita.find_one({"id": contratto["unita_id"]})
                    immobile = await db.immobili.find_one({"id": unita["immobile_id"]}) if unita else None
                    
                    users = await db.users.find(
                        {"ruolo": {"$in": ["supervisore", "gestore"]}, "attivo": True},
                        {"_id": 0}
                    ).to_list(100)
                    
                    urgenza = "URGENTE" if threshold >= 7 else "Avviso"
                    
                    for user in users:
                        await create_notification_async(
                            db,
                            tipo="rata_ritardo",
                            user_id=user["id"],
                            titolo=f"{urgenza}: Rata in ritardo di {giorni_ritardo} giorni",
                            messaggio=f"Rata {rata['periodo']} - € {rata['importo']} per {affittuario['nome'] if affittuario else 'N/A'} ({immobile['titolo'] if immobile else 'N/A'})",
                            payload={
                                "rata_id": rata["id"],
                                "contratto_id": rata["contratto_id"],
                                "giorni_ritardo": giorni_ritardo,
                                "importo": rata["importo"],
                                "tipo_reminder": "rata_ritardo"
                            },
                            destinatario_email=user.get("email")
                        )
        
        logger.info(f"Checked {len(rate_scadute)} late payments")
    
    asyncio.get_event_loop().run_until_complete(run())
    return "Late payment check completed"


@celery_app.task(name='tasks.notifications.check_documenti_scadenza')
def check_documenti_scadenza():
    """Check expiring documents: 30, 7 days before."""
    async def run():
        db = get_db()
        today = date.today()
        thresholds = [30, 7]
        
        for days in thresholds:
            target_date = (today + relativedelta(days=days)).isoformat()
            
            documenti = await db.documenti.find({
                "expiry_date": target_date
            }, {"_id": 0}).to_list(100)
            
            for doc in documenti:
                users = await db.users.find(
                    {"ruolo": {"$in": ["supervisore", "gestore"]}, "attivo": True},
                    {"_id": 0}
                ).to_list(100)
                
                for user in users:
                    await create_notification_async(
                        db,
                        tipo="doc_scadenza",
                        user_id=user["id"],
                        titolo=f"Documento {doc['filename']} scade tra {days} giorni",
                        messaggio=f"Il documento di tipo '{doc['tipo']}' scadrà il {doc['expiry_date']}",
                        payload={
                            "documento_id": doc["id"],
                            "giorni_rimanenti": days,
                            "tipo_reminder": "doc_scadenza"
                        },
                        destinatario_email=user.get("email")
                    )
        
        logger.info(f"Checked document expirations")
    
    asyncio.get_event_loop().run_until_complete(run())
    return "Document expiration check completed"


@celery_app.task(name='tasks.notifications.check_eventi_critici')
def check_eventi_critici():
    """Immediate notification for high severity critical events."""
    async def run():
        db = get_db()
        
        # Find recent high severity events not yet notified
        one_hour_ago = (datetime.now(timezone.utc) - relativedelta(hours=1)).isoformat()
        
        eventi = await db.eventi_critici.find({
            "gravita": "alta",
            "created_at": {"$gte": one_hour_ago}
        }, {"_id": 0}).to_list(100)
        
        for evento in eventi:
            affittuario = await db.soggetti.find_one({"id": evento["affittuario_id"]})
            unita = await db.unita.find_one({"id": evento.get("unita_id")}) if evento.get("unita_id") else None
            immobile = await db.immobili.find_one({"id": unita["immobile_id"]}) if unita else None
            
            # Notify supervisors immediately
            users = await db.users.find(
                {"ruolo": "supervisore", "attivo": True},
                {"_id": 0}
            ).to_list(100)
            
            for user in users:
                await create_notification_async(
                    db,
                    tipo="evento_critico",
                    user_id=user["id"],
                    titolo=f"🚨 EVENTO CRITICO: {evento['tipo'].replace('_', ' ').title()}",
                    messaggio=f"{evento['descrizione_breve']} - {affittuario['nome'] if affittuario else 'N/A'} ({immobile['titolo'] if immobile else 'N/A'})",
                    payload={
                        "evento_id": evento["id"],
                        "gravita": evento["gravita"],
                        "tipo_evento": evento["tipo"],
                        "tipo_reminder": "evento_critico"
                    },
                    destinatario_email=user.get("email")
                )
        
        logger.info(f"Checked {len(eventi)} critical events")
    
    asyncio.get_event_loop().run_until_complete(run())
    return "Critical events check completed"


@celery_app.task(name='tasks.notifications.send_notification')
def send_notification(notifica_id: str):
    """Send a single pending notification."""
    async def run():
        db = get_db()
        
        notifica = await db.notifiche.find_one({"id": notifica_id}, {"_id": 0})
        if not notifica or notifica["stato"] not in ["pending", "failed"]:
            return
        
        if notifica.get("destinatario_email"):
            from utils.email import send_email
            try:
                html = f"""
                <html><body>
                <h2>{notifica['titolo']}</h2>
                <p>{notifica['messaggio']}</p>
                <hr>
                <p style="color:#666;font-size:12px;">EstateWise - Gestione Immobili</p>
                </body></html>
                """
                success = await send_email(notifica["destinatario_email"], notifica["titolo"], html)
                
                tentativi = notifica.get("tentativi", 0) + 1
                
                if success:
                    await db.notifiche.update_one(
                        {"id": notifica_id},
                        {"$set": {"stato": "sent", "sent_at": datetime.now(timezone.utc).isoformat(), "tentativi": tentativi}}
                    )
                else:
                    await db.notifiche.update_one(
                        {"id": notifica_id},
                        {"$set": {"stato": "failed" if tentativi >= 3 else "pending", "tentativi": tentativi, "last_error": "Send failed"}}
                    )
            except Exception as e:
                await db.notifiche.update_one(
                    {"id": notifica_id},
                    {"$set": {"stato": "failed", "tentativi": notifica.get("tentativi", 0) + 1, "last_error": str(e)}}
                )
    
    asyncio.get_event_loop().run_until_complete(run())
    return f"Notification {notifica_id} processed"
