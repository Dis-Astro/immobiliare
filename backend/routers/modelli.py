from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form
from fastapi.responses import FileResponse
from typing import List, Optional, Dict, Any
from pathlib import Path
from datetime import datetime, timezone
import aiofiles
import os
import re
import zipfile
import shutil
import tempfile
from xml.sax.saxutils import escape

from motor.motor_asyncio import AsyncIOMotorDatabase

from models.modello import (
    ModelloDocumento,
    CompilaModelloRequest,
    PreviewCompilazioneRequest,
    PreviewCompilazioneResponse,
)
from models.documento import Documento, LivelloDocumento
from models.user import UserInDB, UserRole
from routers.auth import get_current_user, get_db
from services.audit import log_audit

router = APIRouter(prefix="/modelli", tags=["Modelli Documento"])

UPLOAD_DIR = Path("/data/uploads/modelli")
OUTPUT_DIR = Path("/data/uploads/documenti_generati")
MAX_FILE_SIZE = 25 * 1024 * 1024


def _extract_docx_xml(path: Path) -> str:
    with zipfile.ZipFile(path, "r") as zf:
        parts = []
        for name in zf.namelist():
            if name.startswith("word/") and name.endswith(".xml"):
                try:
                    parts.append(zf.read(name).decode("utf-8", errors="ignore"))
                except Exception:
                    pass
        return "\n".join(parts)


def _extract_placeholders_from_docx(path: Path) -> List[str]:
    xml = _extract_docx_xml(path)
    found = re.findall(r"\{\{\s*([a-zA-Z0-9_.-]+)\s*\}\}", xml)
    return sorted(set(found))


def _replace_docx_placeholders(template_path: Path, output_path: Path, values: Dict[str, Any]) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)
        with zipfile.ZipFile(template_path, "r") as zf:
            zf.extractall(tmp_dir)

        for xml_path in (tmp_dir / "word").rglob("*.xml"):
            text = xml_path.read_text(encoding="utf-8", errors="ignore")
            for key, value in values.items():
                text = re.sub(
                    r"\{\{\s*" + re.escape(key) + r"\s*\}\}",
                    escape("" if value is None else str(value)),
                    text,
                )
            xml_path.write_text(text, encoding="utf-8")

        with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for file_path in tmp_dir.rglob("*"):
                if file_path.is_file():
                    zf.write(file_path, file_path.relative_to(tmp_dir).as_posix())


def _missing_values(placeholders: List[str], values: Dict[str, Any]) -> List[str]:
    return [p for p in placeholders if values.get(p) in (None, "")]


async def _build_contratto_context(db: AsyncIOMotorDatabase, contratto_id: str) -> Dict[str, Any]:
    contratto = await db.contratti.find_one({"id": contratto_id}, {"_id": 0})
    if not contratto:
        raise HTTPException(status_code=404, detail="Contratto non trovato")

    locatore = await db.soggetti.find_one({"id": contratto["locatore_id"]}, {"_id": 0}) or {}
    affittuario = await db.soggetti.find_one({"id": contratto["affittuario_id"]}, {"_id": 0}) or {}
    unita = await db.unita.find_one({"id": contratto["unita_id"]}, {"_id": 0}) or {}
    immobile = await db.immobili.find_one({"id": unita.get("immobile_id")}, {"_id": 0}) if unita else {}
    immobile = immobile or {}

    values = {
        "contratto_id": contratto.get("id"),
        "codice_contratto": contratto.get("codice_contratto"),
        "data_firma": contratto.get("data_firma"),
        "data_inizio": contratto.get("data_inizio"),
        "data_scadenza": contratto.get("data_scadenza"),
        "durata_mesi": contratto.get("durata_mesi"),
        "canone_importo": contratto.get("canone_importo"),
        "periodicita": contratto.get("periodicita"),
        "giorno_scadenza": contratto.get("giorno_scadenza"),
        "deposito_importo": contratto.get("deposito_importo"),
        "locatore_nome": locatore.get("nome"),
        "locatore_email": locatore.get("email"),
        "locatore_cf": locatore.get("cf"),
        "locatore_piva": locatore.get("piva"),
        "affittuario_nome": affittuario.get("nome"),
        "affittuario_email": affittuario.get("email"),
        "affittuario_cf": affittuario.get("cf"),
        "affittuario_piva": affittuario.get("piva"),
        "unita_codice": unita.get("codice_unita"),
        "unita_mq": unita.get("mq"),
        "unita_tipo": unita.get("tipo_immobile"),
        "immobile_codice": immobile.get("codice"),
        "immobile_titolo": immobile.get("titolo"),
        "immobile_indirizzo": immobile.get("indirizzo"),
    }
    return values


@router.get("", response_model=List[ModelloDocumento])
async def list_modelli(
    tipo: Optional[str] = None,
    current_user: UserInDB = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    query = {}
    if tipo:
        query["tipo"] = tipo
    return await db.modelli_documento.find(query, {"_id": 0}).sort("uploaded_at", -1).to_list(200)


@router.post("/upload", response_model=ModelloDocumento)
async def upload_modello(
    file: UploadFile = File(...),
    nome: str = Form(...),
    tipo: str = Form("contratto"),
    descrizione: Optional[str] = Form(None),
    current_user: UserInDB = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    if current_user.ruolo == UserRole.LETTURA:
        raise HTTPException(status_code=403, detail="Permessi insufficienti")

    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File troppo grande")

    suffix = Path(file.filename or "").suffix.lower().lstrip(".")
    if suffix not in {"docx", "pdf"}:
        raise HTTPException(status_code=400, detail="Sono supportati solo file .docx e .pdf")

    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    modello = ModelloDocumento(
        nome=nome,
        tipo=tipo,
        descrizione=descrizione,
        formato=suffix,
        filename=file.filename or f"modello.{suffix}",
        path_storage="",
        mime=file.content_type,
        size_bytes=len(content),
        uploaded_by=current_user.id,
    )
    file_path = UPLOAD_DIR / f"{modello.id}_{modello.filename}"
    async with aiofiles.open(file_path, "wb") as f:
        await f.write(content)

    modello.path_storage = str(file_path)
    if suffix == "docx":
        modello.placeholders = _extract_placeholders_from_docx(file_path)
    else:
        modello.testo_guida = "PDF caricato come modello guida. Per compilazione automatica editabile usare DOCX con placeholder {{campo}}."

    doc = modello.model_dump()
    doc["uploaded_at"] = doc["uploaded_at"].isoformat()
    await db.modelli_documento.insert_one(doc)
    await log_audit(db, "modelli_documento", modello.id, "create", None, doc, current_user.id)
    return modello


@router.post("/{modello_id}/compila")
async def compila_modello(
    modello_id: str,
    payload: CompilaModelloRequest,
    current_user: UserInDB = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    if current_user.ruolo == UserRole.LETTURA:
        raise HTTPException(status_code=403, detail="Permessi insufficienti")

    modello = await db.modelli_documento.find_one({"id": modello_id}, {"_id": 0})
    if not modello:
        raise HTTPException(status_code=404, detail="Modello non trovato")
    if modello.get("formato") != "docx":
        raise HTTPException(status_code=400, detail="La compilazione automatica è disponibile per modelli DOCX")

    values = await _build_contratto_context(db, payload.ref_id)
    values.update(payload.valori_extra or {})

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_name = f"{Path(modello['filename']).stem}_{payload.ref_id[:8]}_{datetime.now().strftime('%Y%m%d%H%M%S')}.docx"
    output_path = OUTPUT_DIR / output_name
    _replace_docx_placeholders(Path(modello["path_storage"]), output_path, values)

    if payload.salva_documento:
        documento = Documento(
            livello=LivelloDocumento.CONTRATTO,
            ref_id=payload.ref_id,
            tipo=f"modello_compilato_{modello.get('tipo', 'documento')}",
            filename=output_name,
            path_storage=str(output_path),
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            uploaded_by=current_user.id,
            size_bytes=os.path.getsize(output_path),
            tag=f"Generato da modello: {modello.get('nome')}",
        )
        doc_dict = documento.model_dump()
        doc_dict["uploaded_at"] = doc_dict["uploaded_at"].isoformat()
        await db.documenti.insert_one(doc_dict)

    return FileResponse(
        str(output_path),
        filename=output_name,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )


@router.post("/{modello_id}/preview", response_model=PreviewCompilazioneResponse)
async def preview_compilazione(
    modello_id: str,
    payload: PreviewCompilazioneRequest,
    current_user: UserInDB = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    modello = await db.modelli_documento.find_one({"id": modello_id}, {"_id": 0})
    if not modello:
        raise HTTPException(status_code=404, detail="Modello non trovato")
    if modello.get("formato") != "docx":
        raise HTTPException(status_code=400, detail="La preview campi è disponibile per modelli DOCX")

    values = await _build_contratto_context(db, payload.ref_id)
    values.update(payload.valori_extra or {})
    placeholders = modello.get("placeholders") or []
    return PreviewCompilazioneResponse(
        modello_id=modello_id,
        placeholders=placeholders,
        valori={p: values.get(p) for p in placeholders},
        mancanti=_missing_values(placeholders, values),
    )


@router.delete("/{modello_id}")
async def delete_modello(
    modello_id: str,
    current_user: UserInDB = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    if current_user.ruolo == UserRole.LETTURA:
        raise HTTPException(status_code=403, detail="Permessi insufficienti")
    existing = await db.modelli_documento.find_one({"id": modello_id}, {"_id": 0})
    if not existing:
        raise HTTPException(status_code=404, detail="Modello non trovato")
    if existing.get("path_storage") and os.path.exists(existing["path_storage"]):
        os.remove(existing["path_storage"])
    await db.modelli_documento.delete_one({"id": modello_id})
    await log_audit(db, "modelli_documento", modello_id, "delete", existing, None, current_user.id)
    return {"message": "Modello eliminato"}
