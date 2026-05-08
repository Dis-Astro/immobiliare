"""
EstateWise - Task Celery per Notifiche

Gestisce le notifiche con logica di escalation:
- rata_scaduta: 1, 7, 15 giorni dopo scadenza
- scadenza_contratto: 365, 30, 1 giorni prima
- documento_scadenza: 30, 7 giorni prima  
- evento_critico_alta: immediato ai supervisori

Deduplicazione tramite idempotency_key su MongoDB.
"""

from celery_app import celery_app
from pymongo import MongoClient
from datetime import date, datetime, timezone, timedelta
from dateutil.relativedelta import relativedelta
import os
import logging

logger = logging.getLogger(__name__)

# MongoDB connection per task Celery (sincrono)
MONGO_URL = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
DB_NAME = os.environ.get('DB_NAME', 'test_database')


def get_db():
    """Ottiene connessione DB sincrona per Celery."""
    client = MongoClient(MONGO_URL)
    return client[DB_NAME]


def generate_idempotency_key(tipo: str, ref_id: str, milestone: int) -> str:
    """Genera chiave idempotenza: tipo:ref_id:milestone"""
    return f"{tipo}:{ref_id}:{milestone}"


def create_notification(
    db,
    tipo: str,
    user_id: str,
    titolo: str,
    messaggio: str,
    payload: dict,
    destinatario_email: str = None,
    ref_type: str = None,
    ref_id: str = None,
    idempotency_key: str = None
) -> dict | None:
    """
    Crea una notifica con controllo di deduplicazione.
    
    Ritorna None se la notifica esiste già (stesso idempotency_key).
    """
    import uuid
    
    # Controllo deduplicazione
    if idempotency_key:
        existing = db.notifiche.find_one({"idempotency_key": idempotency_key})
        if existing:
            logger.info(f"Notifica duplicata skippata: {idempotency_key}")
            return None
    
    notifica = {
        "id": str(uuid.uuid4()),
        "tipo": tipo,
        "user_id": user_id,
        "titolo": titolo,
        "messaggio": messaggio,
        "payload_json": payload,
        "destinatario_email": destinatario_email,
        "idempotency_key": idempotency_key,
        "ref_type": ref_type,
        "ref_id": ref_id,
        "stato": "pending",
        "tentativi": 0,
        "max_tentativi": 3,
        "last_error": None,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    db.notifiche.insert_one(notifica)
    logger.info(f"Notifica creata: {tipo} per user {user_id}")
    
    # Tenta invio email immediato (solo se Celery/Redis è disponibile)
    if destinatario_email:
        try:
            send_notification_email.delay(notifica["id"])
        except Exception as e:
            logger.warning(f"Celery non disponibile, email non inviata: {e}")
            # Marca come pending, verrà inviata quando Celery sarà disponibile
    
    return notifica


@celery_app.task(name='tasks.notifications.send_notification_email', bind=True, max_retries=3)
def send_notification_email(self, notifica_id: str):
    """Invia email per una notifica."""
    import aiosmtplib
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart
    import asyncio
    
    db = get_db()
    notifica = db.notifiche.find_one({"id": notifica_id})
    
    if not notifica or notifica["stato"] == "sent":
        return f"Notifica {notifica_id} già processata o non trovata"
    
    if not notifica.get("destinatario_email"):
        db.notifiche.update_one(
            {"id": notifica_id},
            {"$set": {"stato": "sent", "sent_at": datetime.now(timezone.utc).isoformat()}}
        )
        return f"Notifica {notifica_id} senza email - marcata come sent"
    
    # Configurazione SMTP
    smtp_host = os.environ.get("SMTP_HOST", "")
    smtp_port = int(os.environ.get("SMTP_PORT", "587"))
    smtp_user = os.environ.get("SMTP_USER", "")
    smtp_password = os.environ.get("SMTP_PASSWORD", "")
    smtp_from = os.environ.get("SMTP_FROM", "noreply@estatewise.local")
    
    tentativi = notifica.get("tentativi", 0) + 1
    
    # Se SMTP non configurato, marca come failed senza crash
    if not smtp_host or not smtp_user:
        logger.warning(f"SMTP non configurato. Notifica {notifica_id} marcata failed.")
        db.notifiche.update_one(
            {"id": notifica_id},
            {"$set": {
                "stato": "failed",
                "tentativi": tentativi,
                "last_error": "SMTP non configurato"
            }}
        )
        return f"SMTP non configurato per notifica {notifica_id}"
    
    try:
        # Prepara email
        message = MIMEMultipart("alternative")
        message["From"] = smtp_from
        message["To"] = notifica["destinatario_email"]
        message["Subject"] = notifica["titolo"]
        
        html = f"""
        <html>
        <body style="font-family: Arial, sans-serif; padding: 20px;">
            <h2 style="color: #0F172A;">{notifica['titolo']}</h2>
            <p>{notifica['messaggio']}</p>
            <hr style="border: 1px solid #E2E8F0; margin: 20px 0;">
            <p style="color: #666; font-size: 12px;">
                EstateWise - Gestione Immobili<br>
                Questo è un messaggio automatico.
            </p>
        </body>
        </html>
        """
        message.attach(MIMEText(html, "html"))
        
        # Invia con aiosmtplib (asyncio)
        async def send():
            await aiosmtplib.send(
                message,
                hostname=smtp_host,
                port=smtp_port,
                username=smtp_user,
                password=smtp_password,
                start_tls=True
            )
        
        asyncio.get_event_loop().run_until_complete(send())
        
        # Successo
        db.notifiche.update_one(
            {"id": notifica_id},
            {"$set": {
                "stato": "sent",
                "sent_at": datetime.now(timezone.utc).isoformat(),
                "tentativi": tentativi
            }}
        )
        logger.info(f"Email inviata per notifica {notifica_id}")
        return f"Email inviata: {notifica_id}"
        
    except Exception as e:
        error_msg = str(e)[:500]
        logger.error(f"Errore invio email {notifica_id}: {error_msg}")
        
        # Aggiorna stato
        new_stato = "failed" if tentativi >= 3 else "pending"
        db.notifiche.update_one(
            {"id": notifica_id},
            {"$set": {
                "stato": new_stato,
                "tentativi": tentativi,
                "last_error": error_msg
            }}
        )
        
        # Retry se non al massimo
        if tentativi < 3:
            raise self.retry(exc=e, countdown=60 * tentativi)
        
        return f"Email fallita definitivamente: {notifica_id}"


@celery_app.task(name='tasks.notifications.check_rate_ritardo')
def check_rate_ritardo():
    """
    Controlla rate in ritardo con escalation: 1, 7, 15 giorni.
    Crea notifiche con idempotency_key per evitare duplicati.
    """
    db = get_db()
    today = date.today()
    thresholds = [1, 7, 15]  # Giorni di escalation
    
    # Trova rate non pagate con scadenza passata
    rate_scadute = list(db.rate.find({
        "stato": {"$in": ["da_incassare", "in_ritardo"]},
        "data_scadenza": {"$lt": today.isoformat()}
    }))
    
    notifications_created = 0
    
    for rata in rate_scadute:
        scadenza = date.fromisoformat(rata["data_scadenza"])
        giorni_ritardo = (today - scadenza).days
        
        # Aggiorna stato rata
        db.rate.update_one(
            {"id": rata["id"]},
            {"$set": {"stato": "in_ritardo", "giorni_ritardo": giorni_ritardo}}
        )
        
        # Trova contratto e info correlate
        contratto = db.contratti.find_one({"id": rata["contratto_id"]})
        if not contratto:
            continue
        
        affittuario = db.soggetti.find_one({"id": contratto["affittuario_id"]})
        unita = db.unita.find_one({"id": contratto["unita_id"]})
        immobile = db.immobili.find_one({"id": unita["immobile_id"]}) if unita else None
        
        # Trova utenti destinatari (supervisori e gestori)
        users = list(db.users.find({
            "ruolo": {"$in": ["supervisore", "gestore"]},
            "attivo": True
        }))
        
        # Controlla ogni threshold
        for threshold in thresholds:
            if giorni_ritardo >= threshold:
                urgenza = "🔴 URGENTE" if threshold >= 7 else "⚠️ Avviso"
                
                for user in users:
                    # Genera chiave idempotenza
                    idem_key = generate_idempotency_key("rata_ritardo", rata["id"], threshold)
                    
                    result = create_notification(
                        db,
                        tipo="rata_ritardo",
                        user_id=user["id"],
                        titolo=f"{urgenza}: Rata in ritardo di {giorni_ritardo} giorni",
                        messaggio=f"Rata {rata['periodo']} - € {rata['importo']:,.2f} per {affittuario['nome'] if affittuario else 'N/A'} ({immobile['titolo'] if immobile else 'N/A'}). Scadenza: {rata['data_scadenza']}",
                        payload={
                            "rata_id": rata["id"],
                            "contratto_id": rata["contratto_id"],
                            "giorni_ritardo": giorni_ritardo,
                            "importo": rata["importo"],
                            "threshold": threshold,
                            "tipo_reminder": "rata_ritardo"
                        },
                        destinatario_email=user.get("email"),
                        ref_type="rata",
                        ref_id=rata["id"],
                        idempotency_key=idem_key
                    )
                    if result:
                        notifications_created += 1
    
    logger.info(f"Check rate ritardo completato: {len(rate_scadute)} rate, {notifications_created} notifiche create")
    return f"Rate in ritardo: {len(rate_scadute)}, notifiche: {notifications_created}"


@celery_app.task(name='tasks.notifications.check_scadenze_contratti')
def check_scadenze_contratti():
    """
    Controlla contratti in scadenza: 365, 30, 1 giorni prima.
    """
    db = get_db()
    today = date.today()
    thresholds = [365, 30, 1]  # Giorni prima della scadenza
    
    notifications_created = 0
    
    for days in thresholds:
        target_date = (today + timedelta(days=days)).isoformat()
        
        # Trova contratti che scadono in questa data
        contratti = list(db.contratti.find({
            "stato": "attivo",
            "data_scadenza": target_date
        }))
        
        for contratto in contratti:
            affittuario = db.soggetti.find_one({"id": contratto["affittuario_id"]})
            unita = db.unita.find_one({"id": contratto["unita_id"]})
            immobile = db.immobili.find_one({"id": unita["immobile_id"]}) if unita else None
            
            users = list(db.users.find({
                "ruolo": {"$in": ["supervisore", "gestore"]},
                "attivo": True
            }))
            
            for user in users:
                idem_key = generate_idempotency_key("scadenza_contratto", contratto["id"], days)
                
                result = create_notification(
                    db,
                    tipo="scadenza_contratto",
                    user_id=user["id"],
                    titolo=f"⏰ Contratto {contratto['codice_contratto']} scade tra {days} giorni",
                    messaggio=f"Il contratto con {affittuario['nome'] if affittuario else 'N/A'} per {immobile['titolo'] if immobile else 'N/A'} scadrà il {contratto['data_scadenza']}. Verifica le condizioni di rinnovo.",
                    payload={
                        "contratto_id": contratto["id"],
                        "giorni_rimanenti": days,
                        "data_scadenza": contratto["data_scadenza"],
                        "tipo_reminder": "scadenza_contratto"
                    },
                    destinatario_email=user.get("email"),
                    ref_type="contratto",
                    ref_id=contratto["id"],
                    idempotency_key=idem_key
                )
                if result:
                    notifications_created += 1
    
    logger.info(f"Check scadenze contratti completato: {notifications_created} notifiche")
    return f"Scadenze contratti controllate, notifiche: {notifications_created}"


@celery_app.task(name='tasks.notifications.check_documenti_scadenza')
def check_documenti_scadenza():
    """
    Controlla documenti in scadenza: 30, 7 giorni prima.
    """
    db = get_db()
    today = date.today()
    thresholds = [30, 7]
    
    notifications_created = 0
    
    for days in thresholds:
        target_date = (today + timedelta(days=days)).isoformat()
        
        documenti = list(db.documenti.find({
            "expiry_date": target_date
        }))
        
        for doc in documenti:
            users = list(db.users.find({
                "ruolo": {"$in": ["supervisore", "gestore"]},
                "attivo": True
            }))
            
            for user in users:
                idem_key = generate_idempotency_key("doc_scadenza", doc["id"], days)
                
                result = create_notification(
                    db,
                    tipo="doc_scadenza",
                    user_id=user["id"],
                    titolo=f"📄 Documento '{doc.get('filename', 'N/A')}' scade tra {days} giorni",
                    messaggio=f"Il documento di tipo '{doc.get('tipo', 'N/A')}' scadrà il {doc['expiry_date']}. Provvedi al rinnovo.",
                    payload={
                        "documento_id": doc["id"],
                        "giorni_rimanenti": days,
                        "tipo_documento": doc.get("tipo"),
                        "tipo_reminder": "doc_scadenza"
                    },
                    destinatario_email=user.get("email"),
                    ref_type="documento",
                    ref_id=doc["id"],
                    idempotency_key=idem_key
                )
                if result:
                    notifications_created += 1
    
    logger.info(f"Check documenti scadenza completato: {notifications_created} notifiche")
    return f"Documenti in scadenza controllati, notifiche: {notifications_created}"


@celery_app.task(name='tasks.notifications.check_eventi_critici')
def check_eventi_critici():
    """
    Notifica immediata per eventi critici ad alta gravità ai supervisori.
    """
    db = get_db()
    
    # Trova eventi critici alta gravità non ancora notificati
    one_hour_ago = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
    
    eventi = list(db.eventi_critici.find({
        "gravita": "alta",
        "created_at": {"$gte": one_hour_ago},
        "notificato": {"$ne": True}
    }))
    
    notifications_created = 0
    
    for evento in eventi:
        affittuario = db.soggetti.find_one({"id": evento.get("affittuario_id")})
        unita = db.unita.find_one({"id": evento.get("unita_id")}) if evento.get("unita_id") else None
        immobile = db.immobili.find_one({"id": unita["immobile_id"]}) if unita else None
        
        # Solo supervisori per eventi critici
        users = list(db.users.find({
            "ruolo": "supervisore",
            "attivo": True
        }))
        
        for user in users:
            # Per eventi critici, la chiave usa timestamp per unicità
            idem_key = generate_idempotency_key("evento_critico", evento["id"], 0)
            
            result = create_notification(
                db,
                tipo="evento_critico",
                user_id=user["id"],
                titolo=f"🚨 EVENTO CRITICO: {evento.get('tipo', 'N/A').replace('_', ' ').title()}",
                messaggio=f"{evento.get('descrizione_breve', 'Evento critico registrato')} - {affittuario['nome'] if affittuario else 'N/A'} ({immobile['titolo'] if immobile else 'N/A'}). Richiesta attenzione immediata.",
                payload={
                    "evento_id": evento["id"],
                    "gravita": evento.get("gravita"),
                    "tipo_evento": evento.get("tipo"),
                    "tipo_reminder": "evento_critico"
                },
                destinatario_email=user.get("email"),
                ref_type="evento",
                ref_id=evento["id"],
                idempotency_key=idem_key
            )
            if result:
                notifications_created += 1
        
        # Marca evento come notificato
        db.eventi_critici.update_one(
            {"id": evento["id"]},
            {"$set": {"notificato": True}}
        )
    
    logger.info(f"Check eventi critici completato: {len(eventi)} eventi, {notifications_created} notifiche")
    return f"Eventi critici: {len(eventi)}, notifiche: {notifications_created}"


@celery_app.task(name='tasks.notifications.check_ape_scadenza')
def check_ape_scadenza():
    """
    Controlla APE in scadenza con escalation: 90, 30, 7 giorni prima.
    Notifica anche APE già scaduti (1 volta).
    """
    db = get_db()
    today = date.today()
    thresholds = [90, 30, 7]  # Giorni prima della scadenza

    notifications_created = 0

    # APE in scadenza alle threshold
    for days in thresholds:
        target_date = (today + timedelta(days=days)).isoformat()

        ape_list = list(db.ape.find({
            "data_scadenza": target_date,
            "stato": {"$ne": "sostituito"}
        }))

        for ape in ape_list:
            unita = db.unita.find_one({"id": ape["unita_id"]})
            immobile = db.immobili.find_one({"id": unita["immobile_id"]}) if unita else None

            users = list(db.users.find({
                "ruolo": {"$in": ["supervisore", "gestore"]},
                "attivo": True
            }))

            urgenza = "🔴 URGENTE" if days <= 7 else ("⚠️ Avviso" if days <= 30 else "📅 Promemoria")

            for user in users:
                idem_key = generate_idempotency_key("ape_scadenza", ape["id"], days)
                immobile_titolo = immobile['titolo'] if immobile else 'N/A'
                unita_codice = unita['codice_unita'] if unita else 'N/A'

                result = create_notification(
                    db,
                    tipo="ape_scadenza",
                    user_id=user["id"],
                    titolo=f"{urgenza}: APE classe {ape['classe_energetica']} scade tra {days} giorni",
                    messaggio=(
                        f"L'APE dell'unità {unita_codice} ({immobile_titolo}) scadrà il {ape['data_scadenza']}. "
                        f"Certificatore: {ape.get('certificatore_nome', 'N/A')}. "
                        f"Provvedi al rinnovo."
                    ),
                    payload={
                        "ape_id": ape["id"],
                        "unita_id": ape["unita_id"],
                        "giorni_rimanenti": days,
                        "classe_energetica": ape["classe_energetica"],
                        "data_scadenza": ape["data_scadenza"],
                        "tipo_reminder": "ape_scadenza"
                    },
                    destinatario_email=user.get("email"),
                    ref_type="ape",
                    ref_id=ape["id"],
                    idempotency_key=idem_key
                )
                if result:
                    notifications_created += 1

    # APE scaduti (notifica una volta sola, idempotency con marker -1)
    ape_scaduti = list(db.ape.find({
        "data_scadenza": {"$lt": today.isoformat()},
        "stato": {"$ne": "sostituito"}
    }))

    for ape in ape_scaduti:
        scadenza = date.fromisoformat(ape["data_scadenza"])
        giorni_scaduto = (today - scadenza).days
        if giorni_scaduto > 365:  # Limita a 1 anno per evitare flood
            continue

        unita = db.unita.find_one({"id": ape["unita_id"]})
        immobile = db.immobili.find_one({"id": unita["immobile_id"]}) if unita else None

        # Aggiorna stato APE
        db.ape.update_one(
            {"id": ape["id"]},
            {"$set": {"stato": "scaduto"}}
        )

        users = list(db.users.find({
            "ruolo": {"$in": ["supervisore", "gestore"]},
            "attivo": True
        }))

        for user in users:
            idem_key = generate_idempotency_key("ape_scaduto", ape["id"], -1)
            immobile_titolo = immobile['titolo'] if immobile else 'N/A'
            unita_codice = unita['codice_unita'] if unita else 'N/A'

            result = create_notification(
                db,
                tipo="ape_scaduto",
                user_id=user["id"],
                titolo=f"🔴 APE SCADUTO da {giorni_scaduto} giorni - unità {unita_codice}",
                messaggio=(
                    f"L'APE dell'unità {unita_codice} ({immobile_titolo}) è scaduto il {ape['data_scadenza']}. "
                    f"L'unità non è conforme: l'attestato è obbligatorio per locazioni e atti di vendita."
                ),
                payload={
                    "ape_id": ape["id"],
                    "unita_id": ape["unita_id"],
                    "giorni_scaduto": giorni_scaduto,
                    "tipo_reminder": "ape_scaduto"
                },
                destinatario_email=user.get("email"),
                ref_type="ape",
                ref_id=ape["id"],
                idempotency_key=idem_key
            )
            if result:
                notifications_created += 1

    logger.info(f"Check APE scadenza completato: {notifications_created} notifiche")
    return f"APE scadenze controllate, notifiche: {notifications_created}"


@celery_app.task(name='tasks.notifications.retry_failed_notifications')
def retry_failed_notifications():
    """
    Riprova l'invio di notifiche fallite (max 3 tentativi).
    """
    db = get_db()
    
    # Trova notifiche pending o failed con tentativi < 3
    failed = list(db.notifiche.find({
        "stato": {"$in": ["pending", "failed"]},
        "tentativi": {"$lt": 3},
        "destinatario_email": {"$ne": None}
    }).limit(50))
    
    retried = 0
    for notifica in failed:
        send_notification_email.delay(notifica["id"])
        retried += 1
    
    logger.info(f"Retry notifiche fallite: {retried} task schedulati")
    return f"Notifiche in retry: {retried}"


@celery_app.task(name='tasks.notifications.trigger_manual_check')
def trigger_manual_check(check_type: str = "all"):
    """
    Trigger manuale per testing - esegue i controlli specificati.
    
    Args:
        check_type: "rate", "contratti", "documenti", "eventi", "all"
    """
    results = []
    
    if check_type in ["rate", "all"]:
        results.append(check_rate_ritardo())
    
    if check_type in ["contratti", "all"]:
        results.append(check_scadenze_contratti())
    
    if check_type in ["documenti", "all"]:
        results.append(check_documenti_scadenza())

    if check_type in ["ape", "all"]:
        results.append(check_ape_scadenza())

    if check_type in ["eventi", "all"]:
        results.append(check_eventi_critici())
    
    return f"Check manuale completato: {results}"
