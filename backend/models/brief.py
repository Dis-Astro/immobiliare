"""
Modello configurazione e payload per il Brief AI mattutino via email.
"""
from pydantic import BaseModel, Field, EmailStr, ConfigDict
from typing import List, Optional
from datetime import datetime, timezone


class BriefConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")

    enabled: bool = False
    cron_hour: int = Field(default=8, ge=0, le=23)
    cron_minute: int = Field(default=0, ge=0, le=59)
    recipients: List[EmailStr] = Field(default_factory=list)
    include_rate: bool = True
    include_ape: bool = True
    include_contratti: bool = True
    include_interventi: bool = True
    last_sent_at: Optional[str] = None
    last_status: Optional[str] = None  # 'success' | 'error' | None
    last_error: Optional[str] = None


class BriefConfigUpdate(BaseModel):
    enabled: Optional[bool] = None
    cron_hour: Optional[int] = Field(default=None, ge=0, le=23)
    cron_minute: Optional[int] = Field(default=None, ge=0, le=59)
    recipients: Optional[List[EmailStr]] = None
    include_rate: Optional[bool] = None
    include_ape: Optional[bool] = None
    include_contratti: Optional[bool] = None
    include_interventi: Optional[bool] = None


class BriefPreview(BaseModel):
    """Preview del brief generato (per pulsante 'Invia ora' / anteprima)."""
    summary_html: str
    summary_text: str
    stats: dict
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
