from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from datetime import datetime, date, timezone
from enum import Enum
import uuid


class StatoRata(str, Enum):
    DA_INCASSARE = "da_incassare"
    INCASSATO = "incassato"
    IN_RITARDO = "in_ritardo"
    PARZIALE = "parziale"


class MetodoPagamento(str, Enum):
    BONIFICO = "bonifico"
    CONTANTI = "contanti"
    RID = "rid"
    ALTRO = "altro"


class RataBase(BaseModel):
    contratto_id: str
    periodo: str  # YYYY-MM
    importo: float
    stato: StatoRata = StatoRata.DA_INCASSARE


class RataCreate(RataBase):
    pass


class RataUpdate(BaseModel):
    stato: Optional[StatoRata] = None
    data_incasso: Optional[date] = None
    metodo: Optional[MetodoPagamento] = None
    riferimento: Optional[str] = None
    note: Optional[str] = None
    allegato_contabile_ref: Optional[str] = None
    importo_parziale: Optional[float] = None


class Rata(RataBase):
    model_config = ConfigDict(extra="ignore")
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    data_scadenza: Optional[date] = None
    data_incasso: Optional[date] = None
    metodo: Optional[MetodoPagamento] = None
    riferimento: Optional[str] = None
    note: Optional[str] = None
    allegato_contabile_ref: Optional[str] = None
    giorni_ritardo: int = 0
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    # Campi join per UI
    contratto_codice: Optional[str] = None
    affittuario_nome: Optional[str] = None
    immobile_titolo: Optional[str] = None
