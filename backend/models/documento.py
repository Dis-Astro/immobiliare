from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, Dict, Any
from datetime import datetime, date, timezone
from enum import Enum
import uuid


class LivelloDocumento(str, Enum):
    GENERICO = "generico"
    IMMOBILE = "immobile"
    UNITA = "unita"
    CONTRATTO = "contratto"
    VARIAZIONE = "variazione"
    AFFITTUARIO = "affittuario"
    VERBALE = "verbale"
    SPESA = "spesa"
    INTERVENTO = "intervento"


class DocumentoBase(BaseModel):
    livello: LivelloDocumento
    ref_id: str
    tipo: str  # es: "contratto_firmato", "visura", "planimetria", etc.
    filename: str
    tag: Optional[str] = None
    expiry_date: Optional[date] = None


class DocumentoCreate(DocumentoBase):
    pass


class Documento(DocumentoBase):
    model_config = ConfigDict(extra="ignore")
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    path_storage: str = ""
    mime: Optional[str] = None
    uploaded_by: Optional[str] = None
    uploaded_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    size_bytes: int = 0
    meta_json: Dict[str, Any] = {}
