"""
Modelli per integrazione AI (configurazione provider, sessioni e messaggi chat).
"""

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict, Any, Literal
from datetime import datetime, timezone
from enum import Enum
import uuid


class AiProvider(str, Enum):
    OLLAMA = "ollama"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GEMINI = "gemini"


class AiConfig(BaseModel):
    """Configurazione globale AI (un solo record key='ai_config' in db.config)."""
    model_config = ConfigDict(extra="ignore")

    provider: AiProvider = AiProvider.OLLAMA
    # Ollama settings
    ollama_url: str = "http://ollama:11434"
    ollama_model: str = "llama3.2:3b"
    # Emergent LLM settings (api_key letta da env EMERGENT_LLM_KEY)
    external_model: str = "gpt-5.2"  # modello specifico per il provider scelto
    # Comportamento
    max_context_messages: int = 20
    temperature: float = 0.7
    enabled: bool = True
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_by: Optional[str] = None


class AiConfigUpdate(BaseModel):
    provider: Optional[AiProvider] = None
    ollama_url: Optional[str] = None
    ollama_model: Optional[str] = None
    external_model: Optional[str] = None
    max_context_messages: Optional[int] = None
    temperature: Optional[float] = None
    enabled: Optional[bool] = None


class ChatMessageRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class ChatMessage(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str
    role: ChatMessageRole
    content: str
    metadata: Dict[str, Any] = {}  # es. {tokens_used, model, latency_ms, sources}
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ChatSession(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    titolo: str = "Nuova conversazione"
    provider: AiProvider = AiProvider.OLLAMA
    model: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    message_count: int = 0


class ChatRequest(BaseModel):
    session_id: Optional[str] = None  # se None viene creata nuova sessione
    message: str
    include_context: bool = True  # se True, include dati app come contesto


class AnalyzeDocumentRequest(BaseModel):
    documento_id: Optional[str] = None  # se None usare ape_id
    ape_id: Optional[str] = None
    prompt: str = "Analizza questo documento ed estrai i dati principali in formato strutturato."


class GenerateTextRequest(BaseModel):
    tipo: Literal["clausola_contratto", "email_sollecito", "report_executive", "disdetta", "free"]
    contesto: Dict[str, Any] = {}
    istruzioni: Optional[str] = None


class SuggestRequest(BaseModel):
    """Richiesta di suggerimenti proattivi sul singolo entità (contratto/immobile/etc)."""
    entita_tipo: Literal["contratto", "immobile", "unita", "rata", "ape", "globale"]
    entita_id: Optional[str] = None
