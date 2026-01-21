from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, Dict, Any
from datetime import datetime, date, timezone
from enum import Enum
import uuid


class StatoContratto(str, Enum):
    ATTIVO = "attivo"
    SCADUTO = "scaduto"
    CHIUSO = "chiuso"
    CONTESTATO = "contestato"


class Periodicita(str, Enum):
    MENSILE = "mensile"
    TRIMESTRALE = "trimestrale"
    ANNUALE = "annuale"


class StatoDeposito(str, Enum):
    DA_VERSARE = "da_versare"
    VERSATO = "versato"
    PARZIALE = "parziale"
    RESTITUITO = "restituito"


class ReminderConfig(BaseModel):
    scadenza_contratto: list[int] = [365, 30, 1]
    rata_scaduta: list[int] = [1, 7, 15]
    documento_scadenza: list[int] = [30, 7]


class ContrattoBase(BaseModel):
    unita_id: str
    locatore_id: str
    affittuario_id: str
    data_firma: date
    data_inizio: date
    durata_mesi: int
    canone_importo: float
    periodicita: Periodicita = Periodicita.MENSILE
    giorno_scadenza: int = Field(ge=1, le=28, default=5)
    deposito_importo: Optional[float] = None
    deposito_stato: StatoDeposito = StatoDeposito.DA_VERSARE
    deposito_data: Optional[date] = None
    note: Optional[str] = None
    reminder_config: Optional[ReminderConfig] = None


class ContrattoCreate(ContrattoBase):
    pass


class ContrattoUpdate(BaseModel):
    data_firma: Optional[date] = None
    data_inizio: Optional[date] = None
    durata_mesi: Optional[int] = None
    canone_importo: Optional[float] = None
    periodicita: Optional[Periodicita] = None
    giorno_scadenza: Optional[int] = None
    deposito_importo: Optional[float] = None
    deposito_stato: Optional[StatoDeposito] = None
    deposito_data: Optional[date] = None
    stato: Optional[StatoContratto] = None
    note: Optional[str] = None
    reminder_config: Optional[ReminderConfig] = None


class Contratto(ContrattoBase):
    model_config = ConfigDict(extra="ignore")
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    codice_contratto: str = Field(default_factory=lambda: f"CTR-{datetime.now().strftime('%Y%m%d')}-{str(uuid.uuid4())[:8].upper()}")
    data_scadenza: Optional[date] = None
    stato: StatoContratto = StatoContratto.ATTIVO
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    # Campi join per UI
    unita_codice: Optional[str] = None
    immobile_titolo: Optional[str] = None
    locatore_nome: Optional[str] = None
    affittuario_nome: Optional[str] = None
    affittuario_rating: Optional[float] = None
