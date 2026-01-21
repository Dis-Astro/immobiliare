from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from datetime import datetime, date, timezone
from enum import Enum
import uuid


class StatoRecesso(str, Enum):
    IN_VALUTAZIONE = "in_valutazione"
    ACCETTATO = "accettato"
    CONTESTATO = "contestato"
    CHIUSO = "chiuso"


class RecessoBase(BaseModel):
    contratto_id: str
    data_comunicazione: date
    preavviso_giorni: int
    data_efficacia: date
    note: Optional[str] = None
    allegato_ref: Optional[str] = None


class RecessoCreate(RecessoBase):
    pass


class Recesso(RecessoBase):
    model_config = ConfigDict(extra="ignore")
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    stato: StatoRecesso = StatoRecesso.IN_VALUTAZIONE
    created_by: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    # Campi join
    contratto_codice: Optional[str] = None
    affittuario_nome: Optional[str] = None
