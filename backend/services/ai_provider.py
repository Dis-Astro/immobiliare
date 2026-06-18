"""
Servizio AI con switch tra Ollama (locale) e provider esterni (OpenAI/Anthropic/Gemini via LiteLLM).
Espone un'unica interfaccia send_message() che ritorna la risposta dell'assistente.
"""

import os
import logging
import httpx
from typing import List, Dict, Any, Optional
from motor.motor_asyncio import AsyncIOMotorDatabase

logger = logging.getLogger(__name__)


PROVIDER_MODEL_MAP = {
    "gpt-5.2": ("openai", "gpt-5.2"),
    "gpt-5.1": ("openai", "gpt-5.1"),
    "gpt-5": ("openai", "gpt-5"),
    "gpt-5-mini": ("openai", "gpt-5-mini"),
    "gpt-4o": ("openai", "gpt-4o"),
    "claude-sonnet-4-5": ("anthropic", "claude-sonnet-4-5-20250929"),
    "claude-opus-4-5": ("anthropic", "claude-opus-4-5-20251101"),
    "claude-haiku-4-5": ("anthropic", "claude-haiku-4-5-20251001"),
    "gemini-3-pro": ("gemini", "gemini-3.1-pro-preview"),
    "gemini-3-flash": ("gemini", "gemini-3-flash-preview"),
    "gemini-2.5-pro": ("gemini", "gemini-2.5-pro"),
    "gemini-2.5-flash": ("gemini", "gemini-2.5-flash"),
}


SYSTEM_PROMPT_BASE = """Sei l'assistente AI di EstateWise, un gestionale immobiliare italiano per affitti.
Rispondi sempre in italiano in modo professionale ma conciso.
Hai accesso ai dati dell'azienda: immobili, unità, contratti, soggetti, rate, scadenze, APE, interventi di manutenzione, notifiche.
Quando suggerisci azioni concrete (es. inviare sollecito, generare disdetta) descrivi i passi esatti.
Se ti vengono forniti dati strutturati nel contesto, usa quelli con priorità sulla tua conoscenza generale."""


async def get_ai_config(db: AsyncIOMotorDatabase) -> Dict[str, Any]:
    """Recupera la configurazione AI corrente dal database."""
    config = await db.config.find_one({"key": "ai_config"}, {"_id": 0})
    if not config:
        # Default
        return {
            "key": "ai_config",
            "provider": "ollama",
            "ollama_url": os.environ.get("OLLAMA_URL", "http://ollama:11434"),
            "ollama_model": "llama3.2:3b",
            "external_model": "gpt-5.2",
            "max_context_messages": 20,
            "temperature": 0.7,
            "enabled": True
        }
    return config


async def build_app_context(db: AsyncIOMotorDatabase, max_items: int = 30) -> str:
    """Costruisce contesto sintetico sui dati dell'app da fornire all'AI."""
    parts = ["=== CONTESTO ESTATEWISE ==="]

    # Conteggi globali
    n_immobili = await db.immobili.count_documents({})
    n_unita = await db.unita.count_documents({})
    n_contratti_attivi = await db.contratti.count_documents({"stato": "attivo"})
    n_soggetti = await db.soggetti.count_documents({})
    n_rate_pending = await db.rate.count_documents({"stato": {"$in": ["da_incassare", "in_ritardo"]}})

    parts.append(f"Totale immobili: {n_immobili}")
    parts.append(f"Totale unità: {n_unita}")
    parts.append(f"Contratti attivi: {n_contratti_attivi}")
    parts.append(f"Soggetti: {n_soggetti}")
    parts.append(f"Rate pendenti: {n_rate_pending}")

    # Ultimi immobili
    immobili = await db.immobili.find({}, {"_id": 0, "id": 1, "codice": 1, "titolo": 1, "indirizzo": 1}).limit(max_items).to_list(max_items)
    if immobili:
        parts.append("\n[Immobili (sample)]:")
        for i in immobili[:10]:
            parts.append(f"- {i.get('codice')} | {i.get('titolo')} | {i.get('indirizzo')}")

    # Contratti attivi
    contratti = await db.contratti.find({"stato": "attivo"}, {"_id": 0, "id": 1, "codice_contratto": 1, "data_inizio": 1, "data_fine": 1, "canone_mensile": 1}).limit(max_items).to_list(max_items)
    if contratti:
        parts.append("\n[Contratti attivi]:")
        for c in contratti[:10]:
            parts.append(f"- {c.get('codice_contratto')} | dal {c.get('data_inizio','?')} al {c.get('data_fine','?')} | canone €{c.get('canone_mensile','?')}")

    # Rate in ritardo
    rate_ritardo = await db.rate.find({"stato": "in_ritardo"}, {"_id": 0, "contratto_id": 1, "scadenza": 1, "importo": 1}).limit(15).to_list(15)
    if rate_ritardo:
        parts.append("\n[Rate in ritardo]:")
        for r in rate_ritardo[:10]:
            parts.append(f"- contratto {r.get('contratto_id')[:8]}... scadenza {r.get('scadenza')} importo €{r.get('importo')}")

    # APE in scadenza
    ape_scad = await db.ape.find({"stato": {"$in": ["in_scadenza", "scaduto"]}}, {"_id": 0, "unita_id": 1, "classe_energetica": 1, "data_scadenza": 1, "stato": 1}).limit(15).to_list(15)
    if ape_scad:
        parts.append("\n[APE in scadenza/scaduti]:")
        for a in ape_scad[:10]:
            parts.append(f"- unità {a.get('unita_id')[:8]}... classe {a.get('classe_energetica')} scade il {a.get('data_scadenza')} ({a.get('stato')})")

    return "\n".join(parts)


async def build_entity_context(db: AsyncIOMotorDatabase, entita_tipo: str, entita_id: Optional[str]) -> str:
    """Contesto specifico per una singola entità."""
    parts = [f"=== DETTAGLIO {entita_tipo.upper()} ==="]
    if entita_tipo == "globale" or not entita_id:
        return await build_app_context(db)

    if entita_tipo == "contratto":
        c = await db.contratti.find_one({"id": entita_id}, {"_id": 0})
        if c:
            parts.append(f"Contratto {c.get('codice_contratto')}")
            parts.append(f"Periodo: {c.get('data_inizio')} -> {c.get('data_fine')}")
            parts.append(f"Canone: €{c.get('canone_mensile')}")
            parts.append(f"Stato: {c.get('stato')}")
            rate = await db.rate.find({"contratto_id": entita_id}, {"_id": 0, "scadenza": 1, "stato": 1, "importo": 1}).to_list(50)
            parts.append(f"Rate ({len(rate)}):")
            for r in rate[:20]:
                parts.append(f"  - {r.get('scadenza')} €{r.get('importo')} [{r.get('stato')}]")
    elif entita_tipo == "immobile":
        im = await db.immobili.find_one({"id": entita_id}, {"_id": 0})
        if im:
            parts.append(f"Immobile {im.get('codice')} - {im.get('titolo')}")
            parts.append(f"Indirizzo: {im.get('indirizzo')}")
            unita = await db.unita.find({"immobile_id": entita_id}, {"_id": 0, "codice_unita": 1, "stato": 1, "tipo_immobile": 1, "mq": 1}).to_list(50)
            parts.append(f"Unità ({len(unita)}):")
            for u in unita:
                parts.append(f"  - {u.get('codice_unita')} {u.get('tipo_immobile')} {u.get('mq')}mq [{u.get('stato')}]")
    elif entita_tipo == "unita":
        u = await db.unita.find_one({"id": entita_id}, {"_id": 0})
        if u:
            parts.append(f"Unità {u.get('codice_unita')} - tipo {u.get('tipo_immobile')} {u.get('mq')}mq stato {u.get('stato')}")
            ape = await db.ape.find({"unita_id": entita_id, "stato": {"$ne": "sostituito"}}, {"_id": 0, "classe_energetica": 1, "data_scadenza": 1, "stato": 1}).to_list(5)
            if ape:
                parts.append("APE:")
                for a in ape:
                    parts.append(f"  - classe {a.get('classe_energetica')} scade {a.get('data_scadenza')} ({a.get('stato')})")
    elif entita_tipo == "ape":
        a = await db.ape.find_one({"id": entita_id}, {"_id": 0})
        if a:
            parts.append(f"APE classe {a.get('classe_energetica')} - emesso {a.get('data_emissione')} - scade {a.get('data_scadenza')}")
            parts.append(f"Certificatore: {a.get('certificatore_nome')} ({a.get('certificatore_albo','-')})")
            parts.append(f"Stato: {a.get('stato')}")
    elif entita_tipo == "rata":
        r = await db.rate.find_one({"id": entita_id}, {"_id": 0})
        if r:
            parts.append(f"Rata: scadenza {r.get('scadenza')} importo €{r.get('importo')} stato {r.get('stato')}")
            if r.get("contratto_id"):
                c = await db.contratti.find_one({"id": r["contratto_id"]}, {"_id": 0, "codice_contratto": 1, "canone_mensile": 1})
                if c:
                    parts.append(f"Contratto: {c.get('codice_contratto')} canone €{c.get('canone_mensile')}")

    return "\n".join(parts)


async def call_ollama(
    base_url: str,
    model: str,
    messages: List[Dict[str, str]],
    temperature: float = 0.7
) -> str:
    """Chiama Ollama via API HTTP."""
    url = f"{base_url.rstrip('/')}/api/chat"
    payload = {
        "model": model,
        "messages": messages,
        "stream": False,
        "options": {"temperature": temperature}
    }
    async with httpx.AsyncClient(timeout=120.0) as client:
        try:
            r = await client.post(url, json=payload)
            r.raise_for_status()
            data = r.json()
            return data.get("message", {}).get("content", "")
        except httpx.ConnectError as e:
            logger.error(f"Ollama non raggiungibile a {base_url}: {e}")
            raise RuntimeError(f"Ollama non raggiungibile a {base_url}. Verifica che il servizio sia attivo.")
        except httpx.HTTPStatusError as e:
            logger.error(f"Ollama HTTP {e.response.status_code}: {e.response.text}")
            raise RuntimeError(f"Errore Ollama: {e.response.text}")


async def call_litellm(
    api_key: str,
    system_message: str,
    messages: List[Dict[str, str]],
    model_key: str,
    temperature: float = 0.7
) -> str:
    """Chiama un provider esterno via LiteLLM (openai/anthropic/gemini)."""
    from litellm import acompletion

    if model_key not in PROVIDER_MODEL_MAP:
        raise ValueError(f"Modello esterno non supportato: {model_key}. Disponibili: {list(PROVIDER_MODEL_MAP.keys())}")

    provider, model_name = PROVIDER_MODEL_MAP[model_key]
    full_model = f"{provider}/{model_name}"

    chat_messages = [{"role": "system", "content": system_message}] + messages

    response = await acompletion(
        model=full_model,
        messages=chat_messages,
        api_key=api_key,
        temperature=temperature,
        max_tokens=4096
    )
    return response.choices[0].message.content if response.choices else ""


async def send_chat_message(
    db: AsyncIOMotorDatabase,
    session_id: str,
    user_message: str,
    extra_context: Optional[str] = None,
    history: Optional[List[Dict[str, str]]] = None
) -> Dict[str, Any]:
    """
    Invia un messaggio all'AI configurato e ritorna la risposta.
    Returns: {content, provider, model, latency_ms}
    """
    import time
    config = await get_ai_config(db)
    provider = config.get("provider", "ollama")
    temperature = config.get("temperature", 0.7)

    system_msg = SYSTEM_PROMPT_BASE
    if extra_context:
        system_msg = system_msg + "\n\n" + extra_context

    start = time.time()

    if provider == "ollama":
        ollama_url = config.get("ollama_url", "http://ollama:11434")
        ollama_model = config.get("ollama_model", "llama3.2:3b")

        messages = [{"role": "system", "content": system_msg}]
        if history:
            messages.extend(history)
        messages.append({"role": "user", "content": user_message})

        content = await call_ollama(ollama_url, ollama_model, messages, temperature)
        latency = int((time.time() - start) * 1000)
        return {
            "content": content,
            "provider": "ollama",
            "model": ollama_model,
            "latency_ms": latency
        }
    else:
        # Provider esterno (OpenAI/Anthropic/Gemini) via LiteLLM
        api_key = os.environ.get("EXTERNAL_AI_KEY")
        if not api_key:
            raise RuntimeError("EXTERNAL_AI_KEY non configurato. Imposta la chiave API per provider esterni o passa a Ollama.")

        external_model = config.get("external_model", "gpt-4o")

        chat_messages = []
        if history:
            chat_messages.extend(history)
        chat_messages.append({"role": "user", "content": user_message})

        content = await call_litellm(
            api_key=api_key,
            system_message=system_msg,
            messages=chat_messages,
            model_key=external_model,
            temperature=temperature
        )
        latency = int((time.time() - start) * 1000)
        return {
            "content": content,
            "provider": provider,
            "model": external_model,
            "latency_ms": latency
        }


async def analyze_pdf_document(
    db: AsyncIOMotorDatabase,
    file_path: str,
    file_name: str,
    file_mime: str,
    prompt: str
) -> Dict[str, Any]:
    """
    Analizza un documento (PDF/immagine) usando il provider AI configurato.
    Per Ollama usa estrazione testo locale. Per provider esterni usa chiamata API.
    """
    import time
    _ = await get_ai_config(db)  # caricamento config (riservato a usi futuri)

    # Estrazione testo basica per ogni provider (semplicità + indipendenza)
    text_content = ""
    if file_mime == "application/pdf":
        try:
            import pypdf
            with open(file_path, "rb") as f:
                reader = pypdf.PdfReader(f)
                pages_text = []
                for page in reader.pages[:30]:  # max 30 pagine
                    try:
                        pages_text.append(page.extract_text() or "")
                    except Exception as e:
                        logger.warning(f"Errore estrazione pagina PDF: {e}")
                text_content = "\n\n".join(pages_text)[:15000]  # cap a 15k char
        except ImportError:
            text_content = "[Estrazione PDF non disponibile - pypdf non installato]"
        except Exception as e:
            text_content = f"[Errore lettura PDF: {e}]"
    else:
        text_content = "[Documento non testuale - estrazione non implementata per questo tipo]"

    full_prompt = f"{prompt}\n\n=== CONTENUTO DOCUMENTO ({file_name}) ===\n{text_content}"

    result = await send_chat_message(
        db=db,
        session_id=f"doc-analysis-{int(time.time())}",
        user_message=full_prompt,
        extra_context=None,
        history=None
    )
    return result
