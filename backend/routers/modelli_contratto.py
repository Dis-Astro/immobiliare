from fastapi import APIRouter, HTTPException, Depends, Query, UploadFile, File, Form
from fastapi.responses import Response
from typing import List, Optional, Dict, Any
from datetime import date, datetime, timezone
from pathlib import Path
from html import escape
import os
import re
import zipfile
import xml.etree.ElementTree as ET

import aiofiles
from jinja2 import StrictUndefined, TemplateError
from jinja2.sandbox import SandboxedEnvironment
from motor.motor_asyncio import AsyncIOMotorDatabase
from weasyprint import HTML, CSS

from models.documento import Documento, LivelloDocumento
from models.modello_contratto import (
    FormatoModelloContratto,
    GeneraContrattoRequest,
    ModelloContratto,
    ModelloContrattoCreate,
    ModelloContrattoUpdate,
    TipoModelloContratto,
)
from models.user import UserInDB, UserRole
from routers.auth import get_current_user, get_db
from services.audit import log_audit

router = APIRouter(prefix="/modelli-contratto", tags=["Modelli Contratto"])

UPLOAD_DIR = Path("/data/uploads")
MAX_TEMPLATE_SIZE = 10 * 1024 * 1024

PLACEHOLDER_BLOCK_RE = re.compile(r"(?:{{|{%)(.*?)(?:}}|%})", re.DOTALL)
PLACEHOLDER_TOKEN_RE = re.compile(
    r"\b(?:contratto|locatore|affittuario|unita|immobile|oggi|generated_at)"
    r"(?:\.[A-Za-z_][A-Za-z0-9_]*)*\b"
)

PDF_CSS = """
@page {
    size: A4;
    margin: 2cm;
    @bottom-center {
        content: "Pagina " counter(page) " di " counter(pages);
        font-size: 9pt;
        color: #64748b;
    }
}
body {
    color: #111827;
    font-family: Arial, Helvetica, sans-serif;
    font-size: 11pt;
    line-height: 1.55;
}
h1 { font-size: 20pt; margin: 0 0 18pt; }
h2 { font-size: 15pt; margin-top: 18pt; border-bottom: 1px solid #e5e7eb; padding-bottom: 4pt; }
p { margin: 0 0 9pt; }
table { width: 100%; border-collapse: collapse; margin: 12pt 0; }
td, th { border: 1px solid #d1d5db; padding: 6pt 8pt; vertical-align: top; }
th { background: #f8fafc; }
.signature-row { display: flex; gap: 48pt; margin-top: 48pt; }
.signature-box { flex: 1; text-align: center; border-top: 1px solid #111827; padding-top: 6pt; }
"""

VARIABLES = [
    {"path": "contratto.codice_contratto", "label": "Codice contratto"},
    {"path": "contratto.data_firma", "label": "Data firma"},
    {"path": "contratto.data_inizio", "label": "Data inizio"},
    {"path": "contratto.data_scadenza", "label": "Data scadenza"},
    {"path": "contratto.durata_mesi", "label": "Durata in mesi"},
    {"path": "contratto.canone_importo", "label": "Canone"},
    {"path": "contratto.periodicita", "label": "Periodicita"},
    {"path": "contratto.deposito_importo", "label": "Deposito cauzionale"},
    {"path": "locatore.nome", "label": "Nome locatore"},
    {"path": "locatore.cf", "label": "Codice fiscale locatore"},
    {"path": "locatore.piva", "label": "Partita IVA locatore"},
    {"path": "locatore.email", "label": "Email locatore"},
    {"path": "locatore.telefono", "label": "Telefono locatore"},
    {"path": "locatore.indirizzo", "label": "Indirizzo locatore"},
    {"path": "locatore.pec", "label": "PEC locatore"},
    {"path": "locatore.iban", "label": "IBAN locatore"},
    {"path": "affittuario.nome", "label": "Nome affittuario"},
    {"path": "affittuario.cf", "label": "Codice fiscale affittuario"},
    {"path": "affittuario.piva", "label": "Partita IVA affittuario"},
    {"path": "affittuario.email", "label": "Email affittuario"},
    {"path": "affittuario.telefono", "label": "Telefono affittuario"},
    {"path": "affittuario.indirizzo", "label": "Indirizzo affittuario"},
    {"path": "affittuario.pec", "label": "PEC affittuario"},
    {"path": "unita.codice_unita", "label": "Codice unita"},
    {"path": "unita.tipo_immobile", "label": "Tipo unita"},
    {"path": "unita.mq", "label": "Superficie mq"},
    {"path": "unita.destinazione_uso_attuale", "label": "Destinazione uso"},
    {"path": "immobile.codice", "label": "Codice immobile"},
    {"path": "immobile.titolo", "label": "Nome immobile"},
    {"path": "immobile.indirizzo", "label": "Indirizzo immobile"},
    {"path": "immobile.catastale_comune", "label": "Comune catastale"},
    {"path": "immobile.foglio", "label": "Foglio catastale"},
    {"path": "immobile.particella", "label": "Particella catastale"},
    {"path": "immobile.subalterno", "label": "Subalterno"},
    {"path": "oggi", "label": "Data di generazione"},
]

CONTRATTO_DEFAULT_KEYS = [
    "codice_contratto", "data_firma", "data_inizio", "data_scadenza",
    "durata_mesi", "canone_importo", "periodicita", "deposito_importo",
    "deposito_stato", "deposito_data", "giorno_scadenza", "note",
]
SOGGETTO_DEFAULT_KEYS = ["nome", "cf", "piva", "indirizzo", "pec", "email", "telefono", "iban", "note"]
UNITA_DEFAULT_KEYS = ["codice_unita", "tipo_immobile", "mq", "destinazione_uso_attuale", "note"]
IMMOBILE_DEFAULT_KEYS = [
    "codice", "titolo", "indirizzo", "catastale_comune", "foglio",
    "particella", "subalterno", "categoria", "rendita", "note",
]


def _current_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_filename(filename: Optional[str], fallback: str = "modello") -> str:
    name = Path(filename or fallback).name
    name = re.sub(r"[^A-Za-z0-9._ -]+", "_", name).strip(" .")
    return name or fallback


def _detect_format(filename: str) -> FormatoModelloContratto:
    suffix = Path(filename).suffix.lower()
    if suffix == ".docx":
        return FormatoModelloContratto.DOCX
    if suffix in {".txt", ".md"}:
        return FormatoModelloContratto.TESTO
    return FormatoModelloContratto.HTML


def _format_date(value: Any) -> str:
    if not value:
        return ""
    if isinstance(value, datetime):
        return value.strftime("%d/%m/%Y")
    if isinstance(value, date):
        return value.strftime("%d/%m/%Y")
    if isinstance(value, str):
        raw = value[:10]
        try:
            return date.fromisoformat(raw).strftime("%d/%m/%Y")
        except ValueError:
            return value
    return str(value)


def _format_currency(value: Any) -> str:
    if value is None or value == "":
        return ""
    try:
        amount = f"{float(value):,.2f}"
    except (TypeError, ValueError):
        return str(value)
    amount = amount.replace(",", "X").replace(".", ",").replace("X", ".")
    return f"EUR {amount}"


def _extract_placeholders(contenuto_html: str) -> List[str]:
    variables = set()
    for block in PLACEHOLDER_BLOCK_RE.findall(contenuto_html or ""):
        expression = block.split("|", 1)[0]
        variables.update(PLACEHOLDER_TOKEN_RE.findall(expression))
    return sorted(variables)


def _with_defaults(data: Optional[Dict[str, Any]], keys: List[str]) -> Dict[str, Any]:
    normalized = {key: None for key in keys}
    if data:
        normalized.update(data)
    return normalized


def _html_from_plain_text(text: str) -> str:
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    if not paragraphs:
        return "<p></p>"
    return "\n".join(f"<p>{escape(p).replace(chr(10), '<br>')}</p>" for p in paragraphs)


def _paragraph_text(element: ET.Element, ns: Dict[str, str]) -> str:
    return "".join(node.text or "" for node in element.findall(".//w:t", ns))


def _docx_to_html(content: bytes) -> str:
    ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    try:
        import io

        with zipfile.ZipFile(io.BytesIO(content)) as archive:
            xml_content = archive.read("word/document.xml")
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"DOCX non leggibile: {exc}") from exc

    root = ET.fromstring(xml_content)
    body = root.find("w:body", ns)
    if body is None:
        return "<p></p>"

    chunks = []
    for child in list(body):
        tag = child.tag.rsplit("}", 1)[-1]
        if tag == "p":
            text = _paragraph_text(child, ns).strip()
            if text:
                chunks.append(f"<p>{escape(text)}</p>")
        elif tag == "tbl":
            rows = []
            for tr in child.findall("w:tr", ns):
                cells = []
                for tc in tr.findall("w:tc", ns):
                    parts = [
                        _paragraph_text(p, ns).strip()
                        for p in tc.findall("w:p", ns)
                    ]
                    value = "<br>".join(escape(p) for p in parts if p)
                    cells.append(f"<td>{value}</td>")
                if cells:
                    rows.append(f"<tr>{''.join(cells)}</tr>")
            if rows:
                chunks.append(f"<table>{''.join(rows)}</table>")

    return "\n".join(chunks) or "<p></p>"


def _read_template_file(filename: str, content: bytes) -> tuple[str, FormatoModelloContratto]:
    formato = _detect_format(filename)
    suffix = Path(filename).suffix.lower()

    if formato == FormatoModelloContratto.DOCX:
        return _docx_to_html(content), formato

    if suffix not in {".html", ".htm", ".txt", ".md"}:
        raise HTTPException(status_code=400, detail="Formato non supportato. Usa .html, .htm, .txt, .md o .docx")

    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError:
        text = content.decode("latin-1")

    if formato == FormatoModelloContratto.TESTO:
        return _html_from_plain_text(text), formato
    return text, formato


def _render_template(contenuto_html: str, context: Dict[str, Any]) -> str:
    env = SandboxedEnvironment(autoescape=True, undefined=StrictUndefined)
    env.filters["data_it"] = _format_date
    env.filters["euro"] = _format_currency
    try:
        return env.from_string(contenuto_html).render(**context)
    except TemplateError as exc:
        raise HTTPException(status_code=400, detail=f"Errore nel modello: {exc}") from exc


def _generate_pdf(html_content: str) -> bytes:
    return HTML(string=html_content).write_pdf(stylesheets=[CSS(string=PDF_CSS)])


async def _get_contract_context(db: AsyncIOMotorDatabase, contratto_id: str) -> Dict[str, Any]:
    contratto = await db.contratti.find_one({"id": contratto_id}, {"_id": 0})
    if not contratto:
        raise HTTPException(status_code=404, detail="Contratto non trovato")

    locatore = await db.soggetti.find_one({"id": contratto.get("locatore_id")}, {"_id": 0})
    affittuario = await db.soggetti.find_one({"id": contratto.get("affittuario_id")}, {"_id": 0})
    unita = await db.unita.find_one({"id": contratto.get("unita_id")}, {"_id": 0})
    immobile = None
    if unita:
        immobile = await db.immobili.find_one({"id": unita.get("immobile_id")}, {"_id": 0})

    today = date.today()
    return {
        "contratto": _with_defaults(contratto, CONTRATTO_DEFAULT_KEYS),
        "locatore": _with_defaults(locatore, SOGGETTO_DEFAULT_KEYS),
        "affittuario": _with_defaults(affittuario, SOGGETTO_DEFAULT_KEYS),
        "unita": _with_defaults(unita, UNITA_DEFAULT_KEYS),
        "immobile": _with_defaults(immobile, IMMOBILE_DEFAULT_KEYS),
        "oggi": _format_date(today),
        "generated_at": _current_iso(),
    }


async def _save_generated_document(
    db: AsyncIOMotorDatabase,
    current_user: UserInDB,
    contratto: Dict[str, Any],
    pdf_bytes: bytes,
    filename: str,
) -> Optional[str]:
    unita = await db.unita.find_one({"id": contratto.get("unita_id")}, {"_id": 0})
    immobile = None
    if unita:
        immobile = await db.immobili.find_one({"id": unita.get("immobile_id")}, {"_id": 0})

    base = UPLOAD_DIR / "contratti_generati" / contratto["id"]
    if immobile and unita:
        base = (
            UPLOAD_DIR
            / "immobili"
            / _safe_filename(immobile.get("codice"), "immobile")
            / "unita"
            / _safe_filename(unita.get("codice_unita"), "unita")
            / "contratti"
            / _safe_filename(contratto.get("codice_contratto"), "contratto")
        )

    base.mkdir(parents=True, exist_ok=True)
    output_path = base / filename
    async with aiofiles.open(output_path, "wb") as handle:
        await handle.write(pdf_bytes)

    documento = Documento(
        livello=LivelloDocumento.CONTRATTO,
        ref_id=contratto["id"],
        tipo="contratto_generato",
        filename=filename,
        path_storage=str(output_path),
        mime="application/pdf",
        uploaded_by=current_user.id,
        size_bytes=len(pdf_bytes),
        meta_json={"generato_da_modello": True},
    )
    doc_dict = documento.model_dump(mode="json")
    await db.documenti.insert_one(doc_dict)
    await log_audit(db, "documenti", documento.id, "create", None, doc_dict, current_user.id)
    return documento.id


@router.get("/variabili")
async def list_variabili_modello(
    current_user: UserInDB = Depends(get_current_user),
):
    """Lista placeholder disponibili nei modelli."""
    return {"variabili": VARIABLES}


@router.get("", response_model=List[ModelloContratto])
async def list_modelli_contratto(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    tipo: Optional[TipoModelloContratto] = None,
    attivo: Optional[bool] = None,
    search: Optional[str] = None,
    current_user: UserInDB = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Lista modelli contratto."""
    query: Dict[str, Any] = {}
    if tipo:
        query["tipo"] = tipo.value
    if attivo is not None:
        query["attivo"] = attivo
    if search:
        query["$or"] = [
            {"nome": {"$regex": search, "$options": "i"}},
            {"descrizione": {"$regex": search, "$options": "i"}},
        ]

    return await db.modelli_contratto.find(query, {"_id": 0}).sort("created_at", -1).skip(skip).limit(limit).to_list(limit)


@router.post("", response_model=ModelloContratto)
async def create_modello_contratto(
    data: ModelloContrattoCreate,
    current_user: UserInDB = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Crea modello contratto da HTML."""
    if current_user.ruolo == UserRole.LETTURA:
        raise HTTPException(status_code=403, detail="Permessi insufficienti")

    modello = ModelloContratto(**data.model_dump())
    modello.created_by = current_user.id
    if not modello.variabili_richieste:
        modello.variabili_richieste = _extract_placeholders(modello.contenuto_html)

    modello_dict = modello.model_dump(mode="json")
    await db.modelli_contratto.insert_one(modello_dict)
    await log_audit(db, "modelli_contratto", modello.id, "create", None, modello_dict, current_user.id)
    return modello_dict


@router.post("/upload", response_model=ModelloContratto)
async def upload_modello_contratto(
    file: UploadFile = File(...),
    nome: Optional[str] = Form(None),
    tipo: TipoModelloContratto = Form(TipoModelloContratto.PERSONALIZZATO),
    descrizione: Optional[str] = Form(None),
    attivo: bool = Form(True),
    current_user: UserInDB = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Carica un modello da file HTML, testo o DOCX."""
    if current_user.ruolo == UserRole.LETTURA:
        raise HTTPException(status_code=403, detail="Permessi insufficienti")

    content = await file.read()
    if len(content) > MAX_TEMPLATE_SIZE:
        raise HTTPException(status_code=400, detail="File troppo grande. Max 10MB")

    filename = _safe_filename(file.filename, "modello.html")
    contenuto_html, formato = _read_template_file(filename, content)
    modello = ModelloContratto(
        nome=nome or Path(filename).stem,
        tipo=tipo,
        descrizione=descrizione,
        contenuto_html=contenuto_html,
        variabili_richieste=_extract_placeholders(contenuto_html),
        attivo=attivo,
        formato_origine=formato,
        filename_originale=filename,
        created_by=current_user.id,
        meta_json={"content_type": file.content_type, "size_bytes": len(content)},
    )

    storage_path = UPLOAD_DIR / "modelli_contratto" / modello.id
    storage_path.mkdir(parents=True, exist_ok=True)
    file_path = storage_path / filename
    async with aiofiles.open(file_path, "wb") as handle:
        await handle.write(content)
    modello.path_storage = str(file_path)

    modello_dict = modello.model_dump(mode="json")
    await db.modelli_contratto.insert_one(modello_dict)
    await log_audit(db, "modelli_contratto", modello.id, "create", None, modello_dict, current_user.id)
    return modello_dict


@router.post("/genera")
async def genera_contratto_da_modello(
    data: GeneraContrattoRequest,
    current_user: UserInDB = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Genera un contratto finale partendo da un modello e da un contratto."""
    modello = await db.modelli_contratto.find_one({"id": data.modello_id}, {"_id": 0})
    if not modello:
        raise HTTPException(status_code=404, detail="Modello non trovato")
    if not modello.get("attivo", True):
        raise HTTPException(status_code=400, detail="Modello non attivo")

    context = await _get_contract_context(db, data.contratto_id)
    rendered_html = _render_template(modello["contenuto_html"], context)
    contratto = context["contratto"]
    base_name = _safe_filename(
        f"contratto_{contratto.get('codice_contratto', data.contratto_id)}_{modello.get('nome', 'modello')}",
        "contratto_generato",
    )

    if data.formato == "html":
        return Response(
            content=rendered_html,
            media_type="text/html; charset=utf-8",
            headers={"Content-Disposition": f'attachment; filename="{base_name}.html"'},
        )

    pdf_bytes = _generate_pdf(rendered_html)
    headers = {"Content-Disposition": f'attachment; filename="{base_name}.pdf"'}
    if data.salva_documento:
        documento_id = await _save_generated_document(db, current_user, contratto, pdf_bytes, f"{base_name}.pdf")
        if documento_id:
            headers["X-Documento-Id"] = documento_id

    await log_audit(
        db,
        "modelli_contratto",
        data.modello_id,
        "generate",
        None,
        {"contratto_id": data.contratto_id, "formato": data.formato, "salva_documento": data.salva_documento},
        current_user.id,
    )
    return Response(content=pdf_bytes, media_type="application/pdf", headers=headers)


@router.get("/{modello_id}", response_model=ModelloContratto)
async def get_modello_contratto(
    modello_id: str,
    current_user: UserInDB = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Ottieni dettagli modello contratto."""
    modello = await db.modelli_contratto.find_one({"id": modello_id}, {"_id": 0})
    if not modello:
        raise HTTPException(status_code=404, detail="Modello non trovato")
    return modello


@router.get("/{modello_id}/preview")
async def preview_modello_contratto(
    modello_id: str,
    contratto_id: Optional[str] = None,
    current_user: UserInDB = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Anteprima HTML del modello, opzionalmente renderizzata con un contratto."""
    modello = await db.modelli_contratto.find_one({"id": modello_id}, {"_id": 0})
    if not modello:
        raise HTTPException(status_code=404, detail="Modello non trovato")

    html_content = modello["contenuto_html"]
    if contratto_id:
        context = await _get_contract_context(db, contratto_id)
        html_content = _render_template(html_content, context)

    return Response(content=html_content, media_type="text/html; charset=utf-8")


@router.put("/{modello_id}", response_model=ModelloContratto)
async def update_modello_contratto(
    modello_id: str,
    data: ModelloContrattoUpdate,
    current_user: UserInDB = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Aggiorna modello contratto."""
    if current_user.ruolo == UserRole.LETTURA:
        raise HTTPException(status_code=403, detail="Permessi insufficienti")

    existing = await db.modelli_contratto.find_one({"id": modello_id}, {"_id": 0})
    if not existing:
        raise HTTPException(status_code=404, detail="Modello non trovato")

    update_dict = data.model_dump(exclude_unset=True, mode="json")
    if "contenuto_html" in update_dict and "variabili_richieste" not in update_dict:
        update_dict["variabili_richieste"] = _extract_placeholders(update_dict["contenuto_html"])
    update_dict["updated_at"] = _current_iso()

    await db.modelli_contratto.update_one({"id": modello_id}, {"$set": update_dict})
    await log_audit(db, "modelli_contratto", modello_id, "update", existing, update_dict, current_user.id)

    updated = await db.modelli_contratto.find_one({"id": modello_id}, {"_id": 0})
    return updated


@router.delete("/{modello_id}")
async def delete_modello_contratto(
    modello_id: str,
    current_user: UserInDB = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Elimina modello contratto."""
    if current_user.ruolo == UserRole.LETTURA:
        raise HTTPException(status_code=403, detail="Permessi insufficienti")

    existing = await db.modelli_contratto.find_one({"id": modello_id}, {"_id": 0})
    if not existing:
        raise HTTPException(status_code=404, detail="Modello non trovato")

    path_storage = existing.get("path_storage")
    if path_storage and os.path.exists(path_storage):
        os.remove(path_storage)

    await db.modelli_contratto.delete_one({"id": modello_id})
    await log_audit(db, "modelli_contratto", modello_id, "delete", existing, None, current_user.id)
    return {"message": "Modello eliminato"}
