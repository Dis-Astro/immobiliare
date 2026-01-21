from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List
from datetime import datetime, timezone
from enum import Enum
import uuid


class TipoImmobile(str, Enum):
    APPARTAMENTO = "appartamento"
    UFFICIO = "ufficio"
    NEGOZIO = "negozio"
    MAGAZZINO = "magazzino"
    CAPANNONE = "capannone"
    BOX_AUTO = "box_auto"
    POSTO_AUTO = "posto_auto"
    CANTINA = "cantina"
    TERRENO = "terreno"
    VILLA = "villa"
    LOFT = "loft"
    ATTICO = "attico"
    MANSARDA = "mansarda"
    LOCALE_COMMERCIALE = "locale_commerciale"
    LABORATORIO = "laboratorio"
    ALTRO = "altro"


class DestinazioneUso(str, Enum):
    RESIDENZIALE = "residenziale"
    COMMERCIALE = "commerciale"
    UFFICIO = "ufficio"
    INDUSTRIALE = "industriale"
    DEPOSITO = "deposito"
    PARCHEGGIO = "parcheggio"
    MISTO = "misto"
    ALTRO = "altro"


class UnitaBase(BaseModel):
    immobile_id: str
    codice_unita: str
    tipo_immobile: TipoImmobile
    mq: Optional[float] = None
    destinazione_uso_attuale: Optional[DestinazioneUso] = None
    note: Optional[str] = None
    foto_urls: List[str] = []


class UnitaCreate(UnitaBase):
    pass


class UnitaUpdate(BaseModel):
    codice_unita: Optional[str] = None
    tipo_immobile: Optional[TipoImmobile] = None
    mq: Optional[float] = None
    destinazione_uso_attuale: Optional[DestinazioneUso] = None
    note: Optional[str] = None
    foto_urls: Optional[List[str]] = None


class Unita(UnitaBase):
    model_config = ConfigDict(extra="ignore")
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    # Campi calcolati
    contratto_attivo_id: Optional[str] = None
    affittuario_nome: Optional[str] = None
    stato: str = "libera"  # libera, locata, in_manutenzione


class DestinazioneUsoStorico(BaseModel):
    model_config = ConfigDict(extra="ignore")
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    unita_id: str
    destinazione: DestinazioneUso
    data_inizio: datetime
    data_fine: Optional[datetime] = None
    motivo: Optional[str] = None
    allegati_ref: List[str] = []
