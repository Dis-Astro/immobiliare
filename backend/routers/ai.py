"""
Router AI: configurazione provider, chat, analisi documenti, suggerimenti.
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorDatabase

from models.ai_chat import (
    AiConfig, AiConfigUpdate, AiProvider,
    ChatSession, ChatMessage, ChatMessageRole,
    ChatRequest, AnalyzeDocumentRequest, GenerateTextRequest, SuggestRequest
)
from models.user import UserInDB, UserRole
from routers.auth import get_current_user, get_db
from services.ai_provider import (
    get_ai_config, send_chat_message, build_app_context,
    build_entity_context, analyze_pdf_document, EXTERNAL_MODEL_MAP
)
from services.audit import log_audit

router = APIRouter(prefix="/ai", tags=["AI"])


@router.get("/config")
async def get_config(
    current_user: UserInDB = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """Ottieni configurazione AI corrente."""
    config = await get_ai_config(db)
    # Lista modelli disponibili
    config["available_external_models"] = list(EXTERNAL_MODEL_MAP.keys())
    return config


@router.put("/config")
async def update_config(
    data: AiConfigUpdate,
    current_user: UserInDB = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """Aggiorna configurazione AI (solo supervisori)."""
    if current_user.ruolo != UserRole.SUPERVISORE:
        raise HTTPException(status_code=403, detail="Solo supervisori possono modificare config AI")

    existing = await db.config.find_one({"key": "ai_config"}, {"_id": 0})
    update_data = {k: v for k, v in data.model_dump(exclude_unset=True).items() if v is not None}
    if "provider" in update_data and hasattr(update_data["provider"], "value"):
        update_data["provider"] = update_data["provider"].value
    update_data["updated_at"] = datetime.now(timezone.utc).isoformat()
    update_data["updated_by"] = current_user.id

    if existing:
        await db.config.update_one({"key": "ai_config"}, {"$set": update_data})
    else:
        new_doc = {"key": "ai_config", **update_data}
        # Riempire con default se mancanti
        defaults = {
            "provider": "ollama",
            "ollama_url": "http://ollama:11434",
            "ollama_model": "llama3.2:3b",
            "external_model": "gpt-5.2",
            "max_context_messages": 20,
            "temperature": 0.7,
            "enabled": True
        }
        for k, v in defaults.items():
            new_doc.setdefault(k, v)
        await db.config.insert_one(new_doc)

    await log_audit(db, "ai_config", "ai_config", "update", existing, update_data, current_user.id)
    return await get_ai_config(db)


@router.get("/sessions")
async def list_sessions(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    current_user: UserInDB = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """Lista sessioni chat dell'utente corrente."""
    sessions = await db.ai_chat_sessions.find(
        {"user_id": current_user.id},
        {"_id": 0}
    ).sort("updated_at", -1).skip(skip).limit(limit).to_list(limit)
    return sessions


@router.get("/sessions/{session_id}/messages")
async def get_session_messages(
    session_id: str,
    current_user: UserInDB = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """Messaggi di una sessione chat."""
    session = await db.ai_chat_sessions.find_one({"id": session_id, "user_id": current_user.id}, {"_id": 0})
    if not session:
        raise HTTPException(status_code=404, detail="Sessione non trovata")

    messages = await db.ai_chat_messages.find(
        {"session_id": session_id},
        {"_id": 0}
    ).sort("created_at", 1).to_list(500)
    return {"session": session, "messages": messages}


@router.delete("/sessions/{session_id}")
async def delete_session(
    session_id: str,
    current_user: UserInDB = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """Elimina sessione chat e relativi messaggi."""
    session = await db.ai_chat_sessions.find_one({"id": session_id, "user_id": current_user.id}, {"_id": 0})
    if not session:
        raise HTTPException(status_code=404, detail="Sessione non trovata")

    await db.ai_chat_messages.delete_many({"session_id": session_id})
    await db.ai_chat_sessions.delete_one({"id": session_id})
    return {"message": "Sessione eliminata"}


@router.post("/chat")
async def chat(
    payload: ChatRequest,
    current_user: UserInDB = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """Invia un messaggio all'AI. Crea sessione se session_id è null."""
    config = await get_ai_config(db)
    if not config.get("enabled", True):
        raise HTTPException(status_code=400, detail="AI disabilitata. Abilitala nelle impostazioni.")

    # Recupera o crea sessione
    session_id = payload.session_id
    if not session_id:
        new_session = ChatSession(
            user_id=current_user.id,
            titolo=payload.message[:60] + ("..." if len(payload.message) > 60 else ""),
            provider=AiProvider(config.get("provider", "ollama")),
            model=config.get("ollama_model" if config.get("provider") == "ollama" else "external_model")
        )
        doc = new_session.model_dump()
        doc["created_at"] = doc["created_at"].isoformat()
        doc["updated_at"] = doc["updated_at"].isoformat()
        doc["provider"] = doc["provider"].value if hasattr(doc["provider"], "value") else doc["provider"]
        await db.ai_chat_sessions.insert_one(doc)
        doc.pop("_id", None)
        session_id = new_session.id
    else:
        existing = await db.ai_chat_sessions.find_one({"id": session_id, "user_id": current_user.id}, {"_id": 0})
        if not existing:
            raise HTTPException(status_code=404, detail="Sessione non trovata")

    # Recupera cronologia
    history_docs = await db.ai_chat_messages.find(
        {"session_id": session_id},
        {"_id": 0}
    ).sort("created_at", 1).to_list(config.get("max_context_messages", 20))

    history = [{"role": h["role"], "content": h["content"]} for h in history_docs]

    # Salva messaggio utente
    user_msg = ChatMessage(
        session_id=session_id,
        role=ChatMessageRole.USER,
        content=payload.message
    )
    user_doc = user_msg.model_dump()
    user_doc["created_at"] = user_doc["created_at"].isoformat()
    user_doc["role"] = user_doc["role"].value if hasattr(user_doc["role"], "value") else user_doc["role"]
    await db.ai_chat_messages.insert_one(user_doc)
    user_doc.pop("_id", None)

    # Costruisci contesto app
    extra_context = None
    if payload.include_context:
        try:
            extra_context = await build_app_context(db)
        except Exception as e:
            extra_context = f"[Contesto app non disponibile: {e}]"

    # Chiama AI
    try:
        result = await send_chat_message(
            db=db,
            session_id=session_id,
            user_message=payload.message,
            extra_context=extra_context,
            history=history
        )
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Errore AI: {e}")

    # Salva risposta
    assistant_msg = ChatMessage(
        session_id=session_id,
        role=ChatMessageRole.ASSISTANT,
        content=result["content"],
        metadata={
            "provider": result["provider"],
            "model": result["model"],
            "latency_ms": result["latency_ms"]
        }
    )
    asst_doc = assistant_msg.model_dump()
    asst_doc["created_at"] = asst_doc["created_at"].isoformat()
    asst_doc["role"] = asst_doc["role"].value if hasattr(asst_doc["role"], "value") else asst_doc["role"]
    await db.ai_chat_messages.insert_one(asst_doc)
    asst_doc.pop("_id", None)

    # Aggiorna sessione
    await db.ai_chat_sessions.update_one(
        {"id": session_id},
        {
            "$set": {"updated_at": datetime.now(timezone.utc).isoformat()},
            "$inc": {"message_count": 2}
        }
    )

    return {
        "session_id": session_id,
        "user_message": user_doc,
        "assistant_message": asst_doc
    }


@router.post("/analyze-document")
async def analyze_document(
    payload: AnalyzeDocumentRequest,
    current_user: UserInDB = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """Analizza un documento (PDF/immagine) e ritorna estrazione strutturata."""
    config = await get_ai_config(db)
    if not config.get("enabled", True):
        raise HTTPException(status_code=400, detail="AI disabilitata")

    # Trova file
    file_path = None
    file_name = None
    file_mime = None

    if payload.ape_id:
        ape = await db.ape.find_one({"id": payload.ape_id}, {"_id": 0})
        if not ape:
            raise HTTPException(status_code=404, detail="APE non trovato")
        file_path = ape.get("file_path")
        file_name = ape.get("file_name")
        file_mime = ape.get("file_mime")
    elif payload.documento_id:
        doc = await db.documenti.find_one({"id": payload.documento_id}, {"_id": 0})
        if not doc:
            raise HTTPException(status_code=404, detail="Documento non trovato")
        file_path = doc.get("path_storage")
        file_name = doc.get("filename")
        file_mime = doc.get("mime")
    else:
        raise HTTPException(status_code=400, detail="Specificare documento_id o ape_id")

    if not file_path:
        raise HTTPException(status_code=400, detail="File non disponibile per il documento")

    import os
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail=f"File non trovato sul disco: {file_path}")

    try:
        result = await analyze_pdf_document(
            db=db,
            file_path=file_path,
            file_name=file_name or "documento",
            file_mime=file_mime or "application/pdf",
            prompt=payload.prompt
        )
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Errore analisi: {e}")

    return result


@router.post("/suggest")
async def suggest(
    payload: SuggestRequest,
    current_user: UserInDB = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """Suggerimenti proattivi sulla base di un'entità (es. azioni consigliate per un contratto)."""
    config = await get_ai_config(db)
    if not config.get("enabled", True):
        raise HTTPException(status_code=400, detail="AI disabilitata")

    context = await build_entity_context(db, payload.entita_tipo, payload.entita_id)

    prompt_user = f"""Sulla base dei seguenti dati, fornisci 3-5 azioni concrete e prioritizzate che il gestore dovrebbe considerare.
Per ogni azione indica: titolo, motivazione, urgenza (alta/media/bassa), passi pratici.
Rispondi in formato JSON con array "suggerimenti" di oggetti con quei campi.

{context}"""

    try:
        result = await send_chat_message(
            db=db,
            session_id=f"suggest-{current_user.id}",
            user_message=prompt_user,
            extra_context=None,
            history=None
        )
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Errore AI: {e}")

    return result


@router.post("/generate")
async def generate_text(
    payload: GenerateTextRequest,
    current_user: UserInDB = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """Genera testo (clausola, email, report, disdetta, libero)."""
    config = await get_ai_config(db)
    if not config.get("enabled", True):
        raise HTTPException(status_code=400, detail="AI disabilitata")

    instructions_map = {
        "clausola_contratto": "Genera una clausola contrattuale di locazione professionale in italiano. Stile giuridico e chiaro.",
        "email_sollecito": "Componi un'email di sollecito pagamento cortese ma ferma in italiano. Includi importi, scadenza superata e modalità di pagamento.",
        "report_executive": "Crea un report executive sintetico (max 250 parole) in italiano con bullet point chiave e raccomandazioni.",
        "disdetta": "Redigi una lettera di disdetta contratto di locazione formale in italiano, conforme normativa italiana.",
        "free": payload.istruzioni or "Genera testo secondo le istruzioni fornite."
    }
    base_instructions = instructions_map[payload.tipo]
    user_prompt = base_instructions
    if payload.contesto:
        user_prompt += "\n\nContesto:\n" + "\n".join([f"- {k}: {v}" for k, v in payload.contesto.items()])
    if payload.istruzioni and payload.tipo != "free":
        user_prompt += f"\n\nIstruzioni aggiuntive: {payload.istruzioni}"

    try:
        result = await send_chat_message(
            db=db,
            session_id=f"generate-{current_user.id}",
            user_message=user_prompt,
            extra_context=None,
            history=None
        )
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Errore AI: {e}")

    return result


@router.post("/test-connection")
async def test_connection(
    current_user: UserInDB = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """Testa la connessione con il provider AI configurato."""
    if current_user.ruolo == UserRole.LETTURA:
        raise HTTPException(status_code=403, detail="Permessi insufficienti")

    try:
        result = await send_chat_message(
            db=db,
            session_id=f"test-{current_user.id}",
            user_message="Rispondi solo con: OK",
            extra_context=None,
            history=None
        )
        return {
            "success": True,
            "provider": result["provider"],
            "model": result["model"],
            "latency_ms": result["latency_ms"],
            "response_preview": result["content"][:100]
        }
    except RuntimeError as e:
        return {"success": False, "error": str(e)}
    except Exception as e:
        return {"success": False, "error": f"Errore: {e}"}
