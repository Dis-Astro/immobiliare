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
    pass


class Notifica(NotificaBase):
    model_config = ConfigDict(extra="ignore")
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    stato: StatoNotifica = StatoNotifica.PENDING
    tentativi: int = 0
    last_error: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    sent_at: Optional[datetime] = None
    read_at: Optional[datetime] = None
