from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List
from datetime import datetime, date, timezone
from enum import Enum
import uuid


class CategoriaSpesa(str, Enum):
    MANUTENZIONE_ORDINARIA = "manutenzione_ordinaria"
    MANUTENZIONE_STRAORDINARIA = "manutenzione_straordinaria"
    UTENZE = "utenze"
    TASSE = "tasse"
    ASSICURAZIONE = "assicurazione"
    CONDOMINIO = "condominio"
    PULIZIE = "pulizie"
    GIARDINAGGIO = "giardinaggio"
    SICUREZZA = "sicurezza"
    ALTRO = "altro"


class ImputabileA(str, Enum):
    PROPRIETA = "proprieta"
    AFFITTUARIO = "affittuario"
    CONDIVISA = "condivisa"


class SpesaBase(BaseModel):
    immobile_id: str
    unita_id: Optional[str] = None
    data: date
    categoria: CategoriaSpesa
    importo: float
    fornitore: Optional[str] = None
    imputabile_a: ImputabileA = ImputabileA.PROPRIETA
    note: Optional[str] = None
    allegato_fattura_ref: Optional[str] = None


class SpesaCreate(SpesaBase):
    pass


class SpesaImmobile(SpesaBase):
    model_config = ConfigDict(extra="ignore")
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created_by: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    # Campi join
    immobile_titolo: Optional[str] = None
    unita_codice: Optional[str] = None
