from celery import Celery
import os

# Redis URL from environment
REDIS_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')

celery_app = Celery(
    'estatewise',
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=['tasks.notifications', 'tasks.reports']
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
)

# Celery Beat schedule
celery_app.conf.beat_schedule = {
    'check-scadenze-contratti-daily': {
        'task': 'tasks.notifications.check_scadenze_contratti',
        'schedule': 86400.0,  # Every 24 hours
    },
    'check-rate-ritardo-daily': {
        'task': 'tasks.notifications.check_rate_ritardo',
        'schedule': 86400.0,  # Every 24 hours
    },
    'check-documenti-scadenza-daily': {
        'task': 'tasks.notifications.check_documenti_scadenza',
        'schedule': 86400.0,  # Every 24 hours
    },
    'check-eventi-critici-hourly': {
        'task': 'tasks.notifications.check_eventi_critici',
        'schedule': 3600.0,  # Every hour
    },
}
