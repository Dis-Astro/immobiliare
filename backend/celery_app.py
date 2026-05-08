"""
EstateWise - Celery Application Configuration

Servizi asincroni per notifiche, report e task schedulati.
Utilizza Redis come broker e backend.

Avvio:
  Worker: celery -A celery_app worker --loglevel=info
  Beat:   celery -A celery_app beat --loglevel=info
"""

from celery import Celery
from celery.schedules import crontab
import os

# Redis URL from environment
REDIS_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')

celery_app = Celery(
    'estatewise',
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=['tasks.notifications', 'tasks.reports', 'tasks.brief']
)

# Celery configuration
celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='Europe/Rome',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=600,
    worker_prefetch_multiplier=1,
    broker_connection_retry_on_startup=True,
    result_expires=3600,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
)

# Celery Beat schedule - task schedulati
celery_app.conf.beat_schedule = {
    # Controlla scadenze contratti ogni giorno alle 8:00
    'check-scadenze-contratti-daily': {
        'task': 'tasks.notifications.check_scadenze_contratti',
        'schedule': crontab(hour=8, minute=0),
    },
    # Controlla rate in ritardo ogni giorno alle 9:00
    'check-rate-ritardo-daily': {
        'task': 'tasks.notifications.check_rate_ritardo',
        'schedule': crontab(hour=9, minute=0),
    },
    # Controlla documenti in scadenza ogni giorno alle 8:30
    'check-documenti-scadenza-daily': {
        'task': 'tasks.notifications.check_documenti_scadenza',
        'schedule': crontab(hour=8, minute=30),
    },
    # Controlla APE in scadenza ogni giorno alle 8:45
    'check-ape-scadenza-daily': {
        'task': 'tasks.notifications.check_ape_scadenza',
        'schedule': crontab(hour=8, minute=45),
    },
    # Controlla eventi critici ogni ora
    'check-eventi-critici-hourly': {
        'task': 'tasks.notifications.check_eventi_critici',
        'schedule': crontab(minute=0),  # Ogni ora
    },
    # Retry notifiche fallite ogni 30 minuti
    'retry-failed-notifications': {
        'task': 'tasks.notifications.retry_failed_notifications',
        'schedule': crontab(minute='*/30'),
    },
    # Brief mattutino AI: il task viene chiamato ogni ora al minuto 5,
    # poi al suo interno verifica se l'ora corrente corrisponde a quella configurata
    # in DB (config.brief_config.cron_hour) e se è abilitato.
    'send-morning-brief-hourly-check': {
        'task': 'tasks.brief.send_morning_brief',
        'schedule': crontab(minute=5),
    },
}

# Task routing (opzionale, per future espansioni)
celery_app.conf.task_routes = {
    'tasks.notifications.*': {'queue': 'notifications'},
    'tasks.reports.*': {'queue': 'reports'},
}

# Default queue
celery_app.conf.task_default_queue = 'default'
