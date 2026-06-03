from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, Dict, Any, List, Literal
from datetime import datetime, date, timezone
import uuid


class MovimentoIncasso(BaseModel):
    data_movimento: Optional[date] = None
    importo: float
    causale: str
    ordinante: Optional[str] = None
    riferimento: Optional[str] = None
    raw: Dict[str, Any] = {}


class MatchIncasso(BaseModel):
    movimento: MovimentoIncasso
    rata_id: Optional[str] = None
    score: int = 0
    motivi: List[str] = []
    stato_match: Literal["match_certo", "match_probabile", "da_revisionare", "non_abbinato"]
    rata: Optional[Dict[str, Any]] = None
    duplicato: bool = False


class ImportIncassiPreview(BaseModel):
    matches: List[MatchIncasso]
    total_movimenti: int


class ConfermaIncassoRequest(BaseModel):
    rata_id: str
    importo: float
    data_incasso: Optional[date] = None
    metodo: str = "bonifico"
    riferimento: Optional[str] = None
    note: Optional[str] = None


class ImportIncassiLog(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    filename: str
    total_movimenti: int
    matched_count: int
    duplicate_count: int = 0
    uploaded_by: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
