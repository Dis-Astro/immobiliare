from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict, Any, Literal
from datetime import datetime, timezone
import uuid


class ModelloDocumentoBase(BaseModel):
    nome: str
    tipo: str = "contratto"
    descrizione: Optional[str] = None
    formato: Literal["docx", "pdf"]


class ModelloDocumento(ModelloDocumentoBase):
    model_config = ConfigDict(extra="ignore")

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    filename: str
    path_storage: str
    mime: Optional[str] = None
    size_bytes: int = 0
    placeholders: List[str] = []
    testo_guida: Optional[str] = None
    uploaded_by: Optional[str] = None
    uploaded_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class CompilaModelloRequest(BaseModel):
    ref_tipo: Literal["contratto"]
    ref_id: str
    formato_output: Literal["docx"] = "docx"
    valori_extra: Dict[str, Any] = {}
    salva_documento: bool = True


class PreviewCompilazioneRequest(BaseModel):
    ref_tipo: Literal["contratto"]
    ref_id: str
    valori_extra: Dict[str, Any] = {}


class PreviewCompilazioneResponse(BaseModel):
    modello_id: str
    placeholders: List[str]
    valori: Dict[str, Any]
    mancanti: List[str]
