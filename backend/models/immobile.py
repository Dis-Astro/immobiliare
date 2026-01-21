from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List
from datetime import datetime, timezone
import uuid


class ImmobileBase(BaseModel):
    codice: str
    titolo: str
    indirizzo: str
    lat: Optional[float] = None
    lon: Optional[float] = None
    geo_accuracy: Optional[str] = None
    catastale_comune: Optional[str] = None
    foglio: Optional[str] = None
    particella: Optional[str] = None
    subalterno: Optional[str] = None
    categoria: Optional[str] = None
    rendita: Optional[float] = None
    note: Optional[str] = None
    foto_url: Optional[str] = None


class ImmobileCreate(ImmobileBase):
    pass


class ImmobileUpdate(BaseModel):
    codice: Optional[str] = None
    titolo: Optional[str] = None
    indirizzo: Optional[str] = None
    lat: Optional[float] = None
    lon: Optional[float] = None
    geo_accuracy: Optional[str] = None
    catastale_comune: Optional[str] = None
    foglio: Optional[str] = None
    particella: Optional[str] = None
    subalterno: Optional[str] = None
    categoria: Optional[str] = None
    rendita: Optional[float] = None
    note: Optional[str] = None
    foto_url: Optional[str] = None


class Immobile(ImmobileBase):
    model_config = ConfigDict(extra="ignore")
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    # Campi calcolati
    unita_count: int = 0
    contratti_attivi: int = 0
