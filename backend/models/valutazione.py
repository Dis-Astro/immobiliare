from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from datetime import datetime, timezone
from enum import Enum
import uuid


class GravitaEvento(str, Enum):
    BASSA = "bassa"
    MEDIA = "media"
    ALTA = "alta"


class ValutazioneBase(BaseModel):
    affittuario_id: str
    contratto_id: Optional[str] = None
    # Metriche calcolate automaticamente
    percent_puntualita: Optional[float] = None
    ritardo_medio_giorni: Optional[float] = None
    insoluti_num: int = 0
    score_pagamenti: int = Field(default=100, ge=0, le=100)
    # Rating manuali (1-5 stelle)
    rating_serieta: Optional[int] = Field(default=None, ge=1, le=5)
    rating_comunicazione: Optional[int] = Field(default=None, ge=1, le=5)
    rating_rispetto_immobile: Optional[int] = Field(default=None, ge=1, le=5)
    rating_vicinato: Optional[int] = Field(default=None, ge=1, le=5)
    # Note e classificazione
    note_brevi: Optional[str] = Field(default=None, max_length=500)
    gravita_evento: Optional[GravitaEvento] = None


class ValutazioneCreate(BaseModel):
    affittuario_id: str
    contratto_id: Optional[str] = None
    rating_serieta: Optional[int] = Field(default=None, ge=1, le=5)
    rating_comunicazione: Optional[int] = Field(default=None, ge=1, le=5)
    rating_rispetto_immobile: Optional[int] = Field(default=None, ge=1, le=5)
    rating_vicinato: Optional[int] = Field(default=None, ge=1, le=5)
    note_brevi: Optional[str] = Field(default=None, max_length=500)
    gravita_evento: Optional[GravitaEvento] = None


class ValutazioneAffittuario(ValutazioneBase):
    model_config = ConfigDict(extra="ignore")
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created_by: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class TipoEventoCritico(str, Enum):
    LAMENTELA_VICINATO = "lamentela_vicinato"
    DANNO = "danno"
    CONTESTAZIONE = "contestazione"
    DIFFIDA = "diffida"
    INCURIA = "incuria"
    ALTRO = "altro"


class EventoCriticoBase(BaseModel):
    affittuario_id: str
    unita_id: Optional[str] = None
    contratto_id: Optional[str] = None
    tipo: TipoEventoCritico
    gravita: GravitaEvento
    data_evento: datetime
    descrizione_breve: str = Field(max_length=500)


class EventoCriticoCreate(EventoCriticoBase):
    pass


class EventoCritico(EventoCriticoBase):
    model_config = ConfigDict(extra="ignore")
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created_by: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    # Campi join
    affittuario_nome: Optional[str] = None
    unita_codice: Optional[str] = None
    immobile_titolo: Optional[str] = None
