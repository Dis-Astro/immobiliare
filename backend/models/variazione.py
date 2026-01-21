from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, Dict, Any, List
from datetime import datetime, date, timezone
from enum import Enum
import uuid


class TipoVariazione(str, Enum):
    CAMBIO_AFFITTUARIO = "cambio_affittuario"
    CAMBIO_DESTINAZIONE = "cambio_destinazione"
    PROROGA = "proroga"
    RINEGOZIAZIONE = "rinegoziazione"
    RECESSO = "recesso"


class VariazioneBase(BaseModel):
    contratto_id: str
    tipo: TipoVariazione
    data_efficacia: date
    diff_json: Dict[str, Any] = {}  # {campo: {old: X, new: Y}}
    note: Optional[str] = None
    allegati_ref: List[str] = []


class VariazioneCreate(VariazioneBase):
    pass


class VariazioneContratto(VariazioneBase):
    model_config = ConfigDict(extra="ignore")
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created_by: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    # Campi join
    contratto_codice: Optional[str] = None
