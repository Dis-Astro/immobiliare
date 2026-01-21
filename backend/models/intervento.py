from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime, date, timezone
from enum import Enum
import uuid


class PrioritaIntervento(str, Enum):
    BASSA = "bassa"
    MEDIA = "media"
    ALTA = "alta"
    URGENTE = "urgente"


class StatoIntervento(str, Enum):
    RICHIESTO = "richiesto"
    PIANIFICATO = "pianificato"
    IN_CORSO = "in_corso"
    COMPLETATO = "completato"
    ANNULLATO = "annullato"


class InterventoBase(BaseModel):
    immobile_id: str
    unita_id: Optional[str] = None
    titolo: str
    descrizione: Optional[str] = None
    priorita: PrioritaIntervento = PrioritaIntervento.MEDIA
    stato: StatoIntervento = StatoIntervento.RICHIESTO
    costo_stimato: Optional[float] = None
    costo_finale: Optional[float] = None
    data_richiesta: date = Field(default_factory=lambda: date.today())
    data_pianificata: Optional[date] = None
    data_completamento: Optional[date] = None
    fornitore: Optional[str] = None
    checklist_json: List[Dict[str, Any]] = []
    note: Optional[str] = None
    foto_ref: List[str] = []


class InterventoCreate(InterventoBase):
    pass


class InterventoManutenzione(InterventoBase):
    model_config = ConfigDict(extra="ignore")
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created_by: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    # Campi join
    immobile_titolo: Optional[str] = None
    unita_codice: Optional[str] = None
