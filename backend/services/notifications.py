from datetime import datetime, date, timezone
from typing import Optional, List
from motor.motor_asyncio import AsyncIOMotorDatabase
from dateutil.relativedelta import relativedelta
import uuid
import logging
import asyncio

from models.notifica import Notifica, TipoNotifica, StatoNotifica
from models.valutazione import EventoCritico
from utils.email import (
    send_scadenza_contratto_email,
    send_rata_ritardo_email,
    send_evento_critico_email
)

logger = logging.getLogger(__name__)


class NotificationService:
    """Service for managing notifications."""
    
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
    
    async def create_notification(
        self,
        tipo: TipoNotifica,
        user_id: str,
        titolo: str,
        messaggio: str,
        payload: dict = None,
        destinatario_email: str = None
    ) -> Notifica:
        """Create a new notification."""
        notifica = Notifica(
            tipo=tipo,
            user_id=user_id,
            titolo=titolo,
            messaggio=messaggio,
            payload_json=payload or {},
            destinatario_email=destinatario_email
        )
        
        notifica_dict = notifica.model_dump()
        notifica_dict["created_at"] = notifica_dict["created_at"].isoformat()
        
        await self.db.notifiche.insert_one(notifica_dict)
        return notifica
    
    async def check_scadenze_contratti(self):
        """Check for expiring contracts and create notifications."""
        today = date.today()
        
        # Get default reminder days
        reminder_days = [365, 30, 1]
        
        for days in reminder_days:
            target_date = (today + relativedelta(days=days)).isoformat()
            
            contratti = await self.db.contratti.find({
                "stato": "attivo",
                "data_scadenza": target_date
            }, {"_id": 0}).to_list(100)
            
            for contratto in contratti:
                # Check if notification already sent
                existing = await self.db.notifiche.find_one({
                    "tipo": TipoNotifica.SCADENZA_CONTRATTO.value,
                    "payload_json.contratto_id": contratto["id"],
                    "payload_json.giorni": days
                })
                
                if existing:
                    continue
                
                # Get related data
                affittuario = await self.db.soggetti.find_one({"id": contratto["affittuario_id"]})
                unita = await self.db.unita.find_one({"id": contratto["unita_id"]})
                immobile = await self.db.immobili.find_one({"id": unita["immobile_id"]}) if unita else None
                
                # Create notification for all supervisors and gestors
                users = await self.db.users.find(
                    {"ruolo": {"$in": ["supervisore", "gestore"]}, "attivo": True},
                    {"_id": 0}
                ).to_list(100)
                
                for user in users:
                    await self.create_notification(
                        tipo=TipoNotifica.SCADENZA_CONTRATTO,
                        user_id=user["id"],
                        titolo=f"Contratto in scadenza tra {days} giorni",
                        messaggio=f"Il contratto {contratto['codice_contratto']} con {affittuario['nome'] if affittuario else 'N/A'} scadrà il {contratto['data_scadenza']}",
                        payload={
                            "contratto_id": contratto["id"],
                            "giorni": days,
                            "affittuario": affittuario["nome"] if affittuario else None,
                            "immobile": immobile["titolo"] if immobile else None
                        },
                        destinatario_email=user.get("email")
                    )
                    
                    # Send email
                    if user.get("email"):
                        await send_scadenza_contratto_email(
                            user["email"],
                            contratto["codice_contratto"],
                            days,
                            affittuario["nome"] if affittuario else "N/A",
                            immobile["titolo"] if immobile else "N/A"
                        )
    
    async def check_rate_ritardo(self):
        """Check for late payments and create notifications."""
        today = date.today()
        
        # Find newly late payments
        rate_scadute = await self.db.rate.find({
            "stato": "da_incassare",
            "data_scadenza": {"$lt": today.isoformat()}
        }, {"_id": 0}).to_list(1000)
        
        for rata in rate_scadute:
            scadenza = date.fromisoformat(rata["data_scadenza"])
            giorni_ritardo = (today - scadenza).days
            
            # Update status
            await self.db.rate.update_one(
                {"id": rata["id"]},
                {"$set": {"stato": "in_ritardo", "giorni_ritardo": giorni_ritardo}}
            )
            
            # Check notification thresholds
            thresholds = [1, 7, 15]
            for threshold in thresholds:
                if giorni_ritardo == threshold:
                    # Check if notification exists
                    existing = await self.db.notifiche.find_one({
                        "tipo": TipoNotifica.RATA_RITARDO.value,
                        "payload_json.rata_id": rata["id"],
                        "payload_json.giorni": threshold
                    })
                    
                    if existing:
                        continue
                    
                    # Get related data
                    contratto = await self.db.contratti.find_one({"id": rata["contratto_id"]})
                    affittuario = await self.db.soggetti.find_one({"id": contratto["affittuario_id"]}) if contratto else None
                    
                    # Notify supervisors and gestors
                    users = await self.db.users.find(
                        {"ruolo": {"$in": ["supervisore", "gestore"]}, "attivo": True},
                        {"_id": 0}
                    ).to_list(100)
                    
                    for user in users:
                        await self.create_notification(
                            tipo=TipoNotifica.RATA_RITARDO,
                            user_id=user["id"],
                            titolo=f"Rata in ritardo di {giorni_ritardo} giorni",
                            messaggio=f"La rata {rata['periodo']} del contratto {contratto['codice_contratto'] if contratto else 'N/A'} è in ritardo",
                            payload={
                                "rata_id": rata["id"],
                                "giorni": threshold,
                                "importo": rata["importo"],
                                "contratto_id": rata["contratto_id"]
                            },
                            destinatario_email=user.get("email")
                        )
                        
                        if user.get("email"):
                            await send_rata_ritardo_email(
                                user["email"],
                                contratto["codice_contratto"] if contratto else "N/A",
                                rata["periodo"],
                                giorni_ritardo,
                                rata["importo"],
                                affittuario["nome"] if affittuario else "N/A"
                            )
    
    async def run_scheduled_checks(self):
        """Run all scheduled notification checks."""
        logger.info("Running scheduled notification checks...")
        await self.check_scadenze_contratti()
        await self.check_rate_ritardo()
        logger.info("Scheduled checks completed")


async def create_evento_critico_notification(db: AsyncIOMotorDatabase, evento: EventoCritico):
    """Create notification for critical event."""
    # Get related data
    affittuario = await db.soggetti.find_one({"id": evento.affittuario_id})
    unita = await db.unita.find_one({"id": evento.unita_id}) if evento.unita_id else None
    immobile = await db.immobili.find_one({"id": unita["immobile_id"]}) if unita else None
    
    # Notify all supervisors immediately for high severity
    users = await db.users.find(
        {"ruolo": "supervisore", "attivo": True},
        {"_id": 0}
    ).to_list(100)
    
    service = NotificationService(db)
    
    for user in users:
        await service.create_notification(
            tipo=TipoNotifica.EVENTO_CRITICO,
            user_id=user["id"],
            titolo=f"Evento Critico: {evento.tipo.value.replace('_', ' ').title()}",
            messaggio=evento.descrizione_breve,
            payload={
                "evento_id": evento.id,
                "gravita": evento.gravita.value,
                "affittuario_id": evento.affittuario_id,
                "tipo": evento.tipo.value
            },
            destinatario_email=user.get("email")
        )
        
        if user.get("email"):
            await send_evento_critico_email(
                user["email"],
                evento.tipo.value,
                evento.gravita.value,
                evento.descrizione_breve,
                affittuario["nome"] if affittuario else "N/A",
                immobile["titolo"] if immobile else "N/A"
            )
