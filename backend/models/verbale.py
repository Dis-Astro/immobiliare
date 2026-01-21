from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, Dict, Any, List
from datetime import datetime, date, timezone
from enum import Enum
import uuid


class TipoVerbale(str, Enum):
    CONSEGNA = "consegna"
    RICONSEGNA = "riconsegna"


class StatoAmbiente(str, Enum):
    OTTIMO = "ottimo"
    BUONO = "buono"
    USURATO = "usurato"
    DANNEGGIATO = "danneggiato"


class ChecklistItem(BaseModel):
    ambiente: str  # es: "soggiorno", "cucina", "bagno", etc.
    stato: StatoAmbiente
    note: Optional[str] = None
    foto_refs: List[str] = []


class VerbaleBase(BaseModel):
    contratto_id: str
    tipo: TipoVerbale
    data: date
    checklist: List[ChecklistItem] = []
    note: Optional[str] = None


class VerbaleCreate(VerbaleBase):
    pass


class VerbaleStato(VerbaleBase):
    model_config = ConfigDict(extra="ignore")
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    compilato_da: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    # Campi join
    contratto_codice: Optional[str] = None
    affittuario_nome: Optional[str] = None
    unita_codice: Optional[str] = None
