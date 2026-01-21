from pydantic import BaseModel, Field, EmailStr, ConfigDict
from typing import Optional
from datetime import datetime, timezone
from enum import Enum
import uuid


class TipoSoggetto(str, Enum):
    PERSONA = "persona"
    AZIENDA = "azienda"


class SoggettoBase(BaseModel):
    tipo: TipoSoggetto
    nome: str  # nome o ragione_sociale
    cf: Optional[str] = None
    piva: Optional[str] = None
    indirizzo: Optional[str] = None
    pec: Optional[EmailStr] = None
    email: Optional[EmailStr] = None
    telefono: Optional[str] = None
    iban: Optional[str] = None
    note: Optional[str] = None


class SoggettoCreate(SoggettoBase):
    pass


class SoggettoUpdate(BaseModel):
    tipo: Optional[TipoSoggetto] = None
    nome: Optional[str] = None
    cf: Optional[str] = None
    piva: Optional[str] = None
    indirizzo: Optional[str] = None
    pec: Optional[EmailStr] = None
    email: Optional[EmailStr] = None
    telefono: Optional[str] = None
    iban: Optional[str] = None
    note: Optional[str] = None


class Soggetto(SoggettoBase):
    model_config = ConfigDict(extra="ignore")
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    # Campi calcolati per rating (non persistiti direttamente qui)
    rating_medio: Optional[float] = None
    contratti_count: int = 0
