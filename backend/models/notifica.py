"""
Modello Notifica con supporto per idempotenza.

La chiave di idempotenza (idempotency_key) previene notifiche duplicate
per lo stesso evento usando la combinazione: tipo + ref_id + milestone_day
"""

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, Dict, Any
from datetime import datetime, timezone
from enum import Enum
import uuid


class TipoNotifica(str, Enum):
    SCADENZA_CONTRATTO = "scadenza_contratto"
    RATA_RITARDO = "rata_ritardo"
    DOC_SCADENZA = "doc_scadenza"
    EVENTO_CRITICO = "evento_critico"
    APE_SCADENZA = "ape_scadenza"
    APE_SCADUTO = "ape_scaduto"
    SISTEMA = "sistema"


class StatoNotifica(str, Enum):
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"
    READ = "read"


class NotificaBase(BaseModel):
    tipo: TipoNotifica
    destinatario_email: Optional[str] = None
    user_id: Optional[str] = None
    payload_json: Dict[str, Any] = {}
    titolo: str
    messaggio: str


class NotificaCreate(NotificaBase):
    # Chiave di idempotenza: tipo + ref_id + milestone
    idempotency_key: Optional[str] = None


class Notifica(NotificaBase):
    model_config = ConfigDict(extra="ignore")
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    # Chiave di idempotenza per deduplicazione
    # Formato: "{tipo}:{ref_id}:{milestone_day}" es. "rata_ritardo:rata-123:7"
    idempotency_key: Optional[str] = None
    stato: StatoNotifica = StatoNotifica.PENDING
    tentativi: int = 0
    max_tentativi: int = 3
    last_error: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    sent_at: Optional[datetime] = None
    read_at: Optional[datetime] = None
    # Riferimento all'entità correlata
    ref_type: Optional[str] = None  # contratto, rata, documento, evento
    ref_id: Optional[str] = None


def generate_idempotency_key(tipo: str, ref_id: str, milestone: int) -> str:
    """
    Genera una chiave di idempotenza unica per prevenire duplicati.
    
    Args:
        tipo: Tipo di notifica (rata_ritardo, scadenza_contratto, etc.)
        ref_id: ID dell'entità di riferimento (rata, contratto, documento)
        milestone: Giorno di milestone (1, 7, 15 per ritardi; 365, 30, 1 per scadenze)
    
    Returns:
        Chiave unica nel formato "tipo:ref_id:milestone"
    """
    return f"{tipo}:{ref_id}:{milestone}"
