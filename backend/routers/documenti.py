from fastapi import APIRouter, HTTPException, Depends, Query, UploadFile, File, Form
from typing import List, Optional
from datetime import date
import os
import aiofiles
from pathlib import Path
from motor.motor_asyncio import AsyncIOMotorDatabase

from models.documento import Documento, DocumentoCreate, LivelloDocumento
from models.user import UserInDB, UserRole
from routers.auth import get_current_user, get_db
from services.audit import log_audit

router = APIRouter(prefix="/documenti", tags=["Documenti"])

UPLOAD_DIR = Path("/data/uploads")
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB


@router.get("", response_model=List[Documento])
async def list_documenti(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    livello: Optional[LivelloDocumento] = None,
    ref_id: Optional[str] = None,
    tipo: Optional[str] = None,
    scadenza_entro_giorni: Optional[int] = None,
    current_user: UserInDB = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """Lista documenti con filtri."""
    query = {}
    if livello:
        query["livello"] = livello
    if ref_id:
        query["ref_id"] = ref_id
    if tipo:
        query["tipo"] = tipo
    if scadenza_entro_giorni:
        from dateutil.relativedelta import relativedelta
        target = (date.today() + relativedelta(days=scadenza_entro_giorni)).isoformat()
        query["expiry_date"] = {"$lte": target, "$ne": None}
    
    documenti = await db.documenti.find(query, {"_id": 0}).sort("uploaded_at", -1).skip(skip).limit(limit).to_list(limit)
    return documenti


@router.get("/in-scadenza")
async def get_documenti_in_scadenza(
    giorni: int = Query(30, ge=1),
    current_user: UserInDB = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """Ottieni documenti in scadenza."""
    from dateutil.relativedelta import relativedelta
    target = (date.today() + relativedelta(days=giorni)).isoformat()
    today = date.today().isoformat()
    
    documenti = await db.documenti.find({
        "expiry_date": {"$gte": today, "$lte": target}
    }, {"_id": 0}).sort("expiry_date", 1).to_list(100)
    
    return documenti


@router.post("", response_model=Documento)
async def create_documento(
    data: DocumentoCreate,
    current_user: UserInDB = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """Crea record documento (senza file upload)."""
    if current_user.ruolo == UserRole.LETTURA:
        raise HTTPException(status_code=403, detail="Permessi insufficienti")
    
    documento = Documento(**data.model_dump())
    documento.uploaded_by = current_user.id
    
    doc_dict = documento.model_dump()
    doc_dict["uploaded_at"] = doc_dict["uploaded_at"].isoformat()
    if doc_dict.get("expiry_date"):
        doc_dict["expiry_date"] = doc_dict["expiry_date"].isoformat()
    
    await db.documenti.insert_one(doc_dict)
    await log_audit(db, "documenti", documento.id, "create", None, doc_dict, current_user.id)
    
    return documento


@router.post("/upload")
async def upload_documento(
    file: UploadFile = File(...),
    livello: Optional[LivelloDocumento] = Form(None),
    ref_id: Optional[str] = Form(None),
    tipo: str = Form(...),
    tag: Optional[str] = Form(None),
    expiry_date: Optional[date] = Form(None),
    data_scadenza: Optional[date] = Form(None),
    descrizione: Optional[str] = Form(None),
    immobile_id: Optional[str] = Form(None),
    unita_id: Optional[str] = Form(None),
    contratto_id: Optional[str] = Form(None),
    soggetto_id: Optional[str] = Form(None),
    current_user: UserInDB = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """Upload documento con file."""
    if current_user.ruolo == UserRole.LETTURA:
        raise HTTPException(status_code=403, detail="Permessi insufficienti")
    
    # Check file size
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail=f"File troppo grande. Max {MAX_FILE_SIZE // 1024 // 1024}MB")

    if not livello or not ref_id:
        if contratto_id:
            livello, ref_id = LivelloDocumento.CONTRATTO, contratto_id
        elif unita_id:
            livello, ref_id = LivelloDocumento.UNITA, unita_id
        elif immobile_id:
            livello, ref_id = LivelloDocumento.IMMOBILE, immobile_id
        elif soggetto_id:
            livello, ref_id = LivelloDocumento.AFFITTUARIO, soggetto_id
        else:
            livello, ref_id = LivelloDocumento.GENERICO, "generale"

    expiry = expiry_date or data_scadenza
    
    # Determine storage path based on livello and ref
    if livello == LivelloDocumento.IMMOBILE:
        immobile = await db.immobili.find_one({"id": ref_id}, {"codice": 1})
        if not immobile:
            raise HTTPException(status_code=404, detail="Immobile non trovato")
        storage_path = UPLOAD_DIR / "immobili" / immobile["codice"]
    elif livello == LivelloDocumento.UNITA:
        unita = await db.unita.find_one({"id": ref_id}, {"codice_unita": 1, "immobile_id": 1})
        if not unita:
            raise HTTPException(status_code=404, detail="Unità non trovata")
        immobile = await db.immobili.find_one({"id": unita["immobile_id"]}, {"codice": 1})
        storage_path = UPLOAD_DIR / "immobili" / immobile["codice"] / "unita" / unita["codice_unita"]
    elif livello == LivelloDocumento.CONTRATTO:
        contratto = await db.contratti.find_one({"id": ref_id}, {"codice_contratto": 1, "unita_id": 1})
        if not contratto:
            raise HTTPException(status_code=404, detail="Contratto non trovato")
        unita = await db.unita.find_one({"id": contratto["unita_id"]}, {"codice_unita": 1, "immobile_id": 1})
        immobile = await db.immobili.find_one({"id": unita["immobile_id"]}, {"codice": 1})
        storage_path = UPLOAD_DIR / "immobili" / immobile["codice"] / "unita" / unita["codice_unita"] / "contratti" / contratto["codice_contratto"]
    elif livello == LivelloDocumento.GENERICO:
        storage_path = UPLOAD_DIR / "documenti" / "generale"
    else:
        storage_path = UPLOAD_DIR / livello.value / ref_id
    
    # Create directory
    storage_path.mkdir(parents=True, exist_ok=True)
    
    # Save file
    file_path = storage_path / file.filename
    async with aiofiles.open(file_path, 'wb') as f:
        await f.write(content)
    
    # Create document record
    documento = Documento(
        livello=livello,
        ref_id=ref_id,
        tipo=tipo,
        filename=file.filename,
        path_storage=str(file_path),
        mime=file.content_type,
        uploaded_by=current_user.id,
        size_bytes=len(content),
        tag=tag or descrizione,
        expiry_date=expiry
    )
    
    doc_dict = documento.model_dump()
    doc_dict["uploaded_at"] = doc_dict["uploaded_at"].isoformat()
    if doc_dict.get("expiry_date"):
        doc_dict["expiry_date"] = doc_dict["expiry_date"].isoformat()
    
    await db.documenti.insert_one(doc_dict)
    await log_audit(db, "documenti", documento.id, "create", None, doc_dict, current_user.id)
    
    return documento


@router.get("/{documento_id}", response_model=Documento)
async def get_documento(
    documento_id: str,
    current_user: UserInDB = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """Ottieni dettagli documento."""
    documento = await db.documenti.find_one({"id": documento_id}, {"_id": 0})
    if not documento:
        raise HTTPException(status_code=404, detail="Documento non trovato")
    return documento


@router.delete("/{documento_id}")
async def delete_documento(
    documento_id: str,
    current_user: UserInDB = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """Elimina documento."""
    if current_user.ruolo == UserRole.LETTURA:
        raise HTTPException(status_code=403, detail="Permessi insufficienti")
    
    existing = await db.documenti.find_one({"id": documento_id}, {"_id": 0})
    if not existing:
        raise HTTPException(status_code=404, detail="Documento non trovato")
    
    # Delete file if exists
    if existing.get("path_storage") and os.path.exists(existing["path_storage"]):
        os.remove(existing["path_storage"])
    
    await db.documenti.delete_one({"id": documento_id})
    await log_audit(db, "documenti", documento_id, "delete", existing, None, current_user.id)
    
    return {"message": "Documento eliminato"}
