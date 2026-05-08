"""
Modello APE (Attestato di Prestazione Energetica).
Ogni unità immobiliare può avere un APE con scadenza, classe energetica e file PDF.
"""

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime, date, timezone
from enum import Enum
import uuid


class ClasseEnergetica(str, Enum):
    A4 = "A4"
    A3 = "A3"
    A2 = "A2"
    A1 = "A1"
    B = "B"
    C = "C"
    D = "D"
    E = "E"
    F = "F"
    G = "G"


class ZonaClimatica(str, Enum):
    A = "A"
    B = "B"
    C = "C"
    D = "D"
    E = "E"
    F = "F"


class StatoApe(str, Enum):
    VALIDO = "valido"
    IN_SCADENZA = "in_scadenza"  # entro 90gg
    SCADUTO = "scaduto"
    SOSTITUITO = "sostituito"  # esiste un APE successivo per la stessa unità


class ApeBase(BaseModel):
    unita_id: str
    classe_energetica: ClasseEnergetica
    data_emissione: date
    data_scadenza: date  # default da calcolare a +10 anni in client/api
    certificatore_nome: str
    certificatore_albo: Optional[str] = None  # numero iscrizione albo
    zona_climatica: Optional[ZonaClimatica] = None
    epgl_nren: Optional[float] = None  # EPgl,nren in kWh/m²/anno
    superficie_utile_mq: Optional[float] = None
    note: Optional[str] = None


class ApeCreate(ApeBase):
    pass


class ApeUpdate(BaseModel):
    classe_energetica: Optional[ClasseEnergetica] = None
    data_emissione: Optional[date] = None
    data_scadenza: Optional[date] = None
    certificatore_nome: Optional[str] = None
    certificatore_albo: Optional[str] = None
    zona_climatica: Optional[ZonaClimatica] = None
    epgl_nren: Optional[float] = None
    superficie_utile_mq: Optional[float] = None
    note: Optional[str] = None


class RimandoScadenzaInput(BaseModel):
    """Input per rimandare la scadenza di un APE."""
    nuova_scadenza: date
    motivazione: str


class StoricoModifica(BaseModel):
    """Traccia modifica scadenza/sostituzione file."""
    timestamp: datetime
    user_id: str
    user_nome: Optional[str] = None
    azione: str  # "rimando_scadenza" | "sostituzione_file" | "rinnovo"
    valore_precedente: Optional[str] = None
    valore_nuovo: Optional[str] = None
    motivazione: Optional[str] = None


class Ape(ApeBase):
    model_config = ConfigDict(extra="ignore")

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    file_path: Optional[str] = None
    file_name: Optional[str] = None
    file_mime: Optional[str] = None
    file_size_bytes: int = 0
    stato: StatoApe = StatoApe.VALIDO
    storico_modifiche: List[StoricoModifica] = []
    created_by: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    # Campi calcolati per join
    unita_codice: Optional[str] = None
    immobile_id: Optional[str] = None
    immobile_titolo: Optional[str] = None
    giorni_alla_scadenza: Optional[int] = None
