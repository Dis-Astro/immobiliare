from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, Dict, Any, List, Literal
from datetime import datetime, timezone
from enum import Enum
import uuid


class TipoModelloContratto(str, Enum):
    RESIDENZIALE = "residenziale"
    COMMERCIALE = "commerciale"
    TRANSITORIO = "transitorio"
    STUDENTI = "studenti"
    PERSONALIZZATO = "personalizzato"


class FormatoModelloContratto(str, Enum):
    HTML = "html"
    DOCX = "docx"
    TESTO = "testo"


class ModelloContrattoBase(BaseModel):
    nome: str
    tipo: TipoModelloContratto = TipoModelloContratto.PERSONALIZZATO
    descrizione: Optional[str] = None
    contenuto_html: str  # Template HTML con placeholder Jinja2
    variabili_richieste: List[str] = Field(default_factory=list)  # es. ["contratto.codice_contratto", "affittuario.nome"]
    attivo: bool = True
    formato_origine: FormatoModelloContratto = FormatoModelloContratto.HTML
    filename_originale: Optional[str] = None
    path_storage: Optional[str] = None
    meta_json: Dict[str, Any] = Field(default_factory=dict)


class ModelloContrattoCreate(ModelloContrattoBase):
    pass


class ModelloContrattoUpdate(BaseModel):
    nome: Optional[str] = None
    tipo: Optional[TipoModelloContratto] = None
    descrizione: Optional[str] = None
    contenuto_html: Optional[str] = None
    variabili_richieste: Optional[List[str]] = None
    attivo: Optional[bool] = None
    formato_origine: Optional[FormatoModelloContratto] = None
    filename_originale: Optional[str] = None
    path_storage: Optional[str] = None
    meta_json: Optional[Dict[str, Any]] = None


class ModelloContratto(ModelloContrattoBase):
    model_config = ConfigDict(extra="ignore")
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created_by: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: Optional[datetime] = None


class GeneraContrattoRequest(BaseModel):
    modello_id: str
    contratto_id: str
    formato: Literal["pdf", "html"] = "pdf"
    salva_documento: bool = False
