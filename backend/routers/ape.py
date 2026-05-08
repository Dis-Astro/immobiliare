"""
Router per gestione APE (Attestato di Prestazione Energetica).
Operazioni: CRUD, upload/sostituzione file, rimando scadenza, lista in scadenza.
"""

from fastapi import APIRouter, HTTPException, Depends, Query, UploadFile, File, Form
from typing import List, Optional
from datetime import date, datetime, timezone, timedelta
from pathlib import Path
import aiofiles
import os
from motor.motor_asyncio import AsyncIOMotorDatabase

from models.ape import (
    Ape, ApeCreate, ApeUpdate, RimandoScadenzaInput,
    ClasseEnergetica, ZonaClimatica, StatoApe, StoricoModifica
)
from models.user import UserInDB, UserRole
from routers.auth import get_current_user, get_db
from services.audit import log_audit

router = APIRouter(prefix="/ape", tags=["APE"])

UPLOAD_DIR = Path("/data/uploads")
APE_DIR = UPLOAD_DIR / "ape"
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
ALLOWED_MIMES = {"application/pdf", "image/png", "image/jpeg", "image/jpg"}


def _today() -> date:
    return date.today()


def _calc_stato(scadenza: date) -> StatoApe:
    today = _today()
    if scadenza < today:
        return StatoApe.SCADUTO
    if (scadenza - today).days <= 90:
        return StatoApe.IN_SCADENZA
    return StatoApe.VALIDO


def _calc_giorni_scadenza(scadenza_iso: str) -> int:
    if not scadenza_iso:
        return None
    try:
        sc = date.fromisoformat(scadenza_iso[:10])
        return (sc - _today()).days
    except (ValueError, TypeError):
        return None


def _serialize_ape_for_db(ape_obj: Ape) -> dict:
    d = ape_obj.model_dump()
    d["data_emissione"] = d["data_emissione"].isoformat() if d.get("data_emissione") else None
    d["data_scadenza"] = d["data_scadenza"].isoformat() if d.get("data_scadenza") else None
    d["created_at"] = d["created_at"].isoformat()
    d["updated_at"] = d["updated_at"].isoformat()
    storico = []
    for s in d.get("storico_modifiche", []):
        if isinstance(s.get("timestamp"), datetime):
            s["timestamp"] = s["timestamp"].isoformat()
        storico.append(s)
    d["storico_modifiche"] = storico
    return d


async def _enrich_ape(db: AsyncIOMotorDatabase, ape_doc: dict) -> dict:
    """Arricchisce un APE con dati unità/immobile e giorni scadenza."""
    ape_doc["giorni_alla_scadenza"] = _calc_giorni_scadenza(ape_doc.get("data_scadenza"))
    if ape_doc.get("unita_id"):
        unita = await db.unita.find_one(
            {"id": ape_doc["unita_id"]},
            {"_id": 0, "codice_unita": 1, "immobile_id": 1}
        )
        if unita:
            ape_doc["unita_codice"] = unita.get("codice_unita")
            ape_doc["immobile_id"] = unita.get("immobile_id")
            if unita.get("immobile_id"):
                immobile = await db.immobili.find_one(
                    {"id": unita["immobile_id"]},
                    {"_id": 0, "titolo": 1}
                )
                if immobile:
                    ape_doc["immobile_titolo"] = immobile.get("titolo")
    # Ricalcola stato in caso non sia aggiornato (preserva 'sostituito')
    sc = ape_doc.get("data_scadenza")
    if sc and ape_doc.get("stato") != StatoApe.SOSTITUITO.value:
        try:
            ape_doc["stato"] = _calc_stato(date.fromisoformat(sc[:10])).value
        except (ValueError, TypeError):
            pass
    return ape_doc


@router.get("")
async def list_ape(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    unita_id: Optional[str] = None,
    immobile_id: Optional[str] = None,
    classe: Optional[ClasseEnergetica] = None,
    stato: Optional[StatoApe] = None,
    in_scadenza_giorni: Optional[int] = Query(None, ge=1),
    current_user: UserInDB = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """Lista APE con filtri."""
    query = {}
    if unita_id:
        query["unita_id"] = unita_id
    if classe:
        query["classe_energetica"] = classe.value
    if stato:
        query["stato"] = stato.value
    if in_scadenza_giorni:
        target = (_today() + timedelta(days=in_scadenza_giorni)).isoformat()
        today_iso = _today().isoformat()
        query["data_scadenza"] = {"$gte": today_iso, "$lte": target}

    if immobile_id:
        # Filtro tramite unità appartenenti all'immobile
        unita_ids = await db.unita.distinct("id", {"immobile_id": immobile_id})
        query["unita_id"] = {"$in": unita_ids}

    docs = await db.ape.find(query, {"_id": 0}).sort("data_scadenza", 1).skip(skip).limit(limit).to_list(limit)
    enriched = [await _enrich_ape(db, d) for d in docs]
    return enriched


@router.get("/in-scadenza")
async def list_in_scadenza(
    giorni: int = Query(90, ge=1, le=365),
    current_user: UserInDB = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """APE in scadenza entro N giorni."""
    target = (_today() + timedelta(days=giorni)).isoformat()
    today_iso = _today().isoformat()
    docs = await db.ape.find({
        "data_scadenza": {"$gte": today_iso, "$lte": target}
    }, {"_id": 0}).sort("data_scadenza", 1).to_list(200)
    return [await _enrich_ape(db, d) for d in docs]


@router.get("/scaduti")
async def list_scaduti(
    current_user: UserInDB = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """APE scaduti."""
    today_iso = _today().isoformat()
    docs = await db.ape.find({
        "data_scadenza": {"$lt": today_iso}
    }, {"_id": 0}).sort("data_scadenza", -1).to_list(200)
    return [await _enrich_ape(db, d) for d in docs]


@router.get("/by-unita/{unita_id}")
async def get_ape_by_unita(
    unita_id: str,
    current_user: UserInDB = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """Tutti gli APE di una specifica unità (storico incluso)."""
    docs = await db.ape.find(
        {"unita_id": unita_id}, {"_id": 0}
    ).sort("data_emissione", -1).to_list(50)
    return [await _enrich_ape(db, d) for d in docs]


@router.get("/{ape_id}")
async def get_ape(
    ape_id: str,
    current_user: UserInDB = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """Dettaglio singolo APE."""
    doc = await db.ape.find_one({"id": ape_id}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="APE non trovato")
    return await _enrich_ape(db, doc)


@router.post("")
async def create_ape(
    data: ApeCreate,
    current_user: UserInDB = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """Crea nuovo APE (senza file - usare /upload per file)."""
    if current_user.ruolo == UserRole.LETTURA:
        raise HTTPException(status_code=403, detail="Permessi insufficienti")

    # Verifica unità esistente
    unita = await db.unita.find_one({"id": data.unita_id}, {"_id": 0, "id": 1})
    if not unita:
        raise HTTPException(status_code=404, detail="Unità non trovata")

    # Marca eventuali APE precedenti come "sostituito"
    await db.ape.update_many(
        {"unita_id": data.unita_id, "stato": {"$ne": StatoApe.SOSTITUITO.value}},
        {"$set": {"stato": StatoApe.SOSTITUITO.value, "updated_at": datetime.now(timezone.utc).isoformat()}}
    )

    ape = Ape(**data.model_dump())
    ape.created_by = current_user.id
    ape.stato = _calc_stato(ape.data_scadenza)

    doc = _serialize_ape_for_db(ape)
    await db.ape.insert_one(doc)
    doc.pop("_id", None)
    await log_audit(db, "ape", ape.id, "create", None, doc, current_user.id)

    return await _enrich_ape(db, doc)


@router.post("/upload")
async def create_ape_with_file(
    file: UploadFile = File(...),
    unita_id: str = Form(...),
    classe_energetica: ClasseEnergetica = Form(...),
    data_emissione: date = Form(...),
    data_scadenza: date = Form(...),
    certificatore_nome: str = Form(...),
    certificatore_albo: Optional[str] = Form(None),
    zona_climatica: Optional[ZonaClimatica] = Form(None),
    epgl_nren: Optional[float] = Form(None),
    superficie_utile_mq: Optional[float] = Form(None),
    note: Optional[str] = Form(None),
    current_user: UserInDB = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """Crea nuovo APE con upload del file PDF/immagine."""
    if current_user.ruolo == UserRole.LETTURA:
        raise HTTPException(status_code=403, detail="Permessi insufficienti")

    # Verifica unità
    unita = await db.unita.find_one({"id": unita_id}, {"_id": 0, "id": 1, "codice_unita": 1})
    if not unita:
        raise HTTPException(status_code=404, detail="Unità non trovata")

    # Validazione file
    if file.content_type not in ALLOWED_MIMES:
        raise HTTPException(status_code=400, detail=f"Tipo file non supportato. Ammessi: PDF, PNG, JPEG")

    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail=f"File troppo grande. Max {MAX_FILE_SIZE // 1024 // 1024}MB")

    # Storage
    storage_dir = APE_DIR / unita_id
    storage_dir.mkdir(parents=True, exist_ok=True)
    ape_id = None
    ape = Ape(
        unita_id=unita_id,
        classe_energetica=classe_energetica,
        data_emissione=data_emissione,
        data_scadenza=data_scadenza,
        certificatore_nome=certificatore_nome,
        certificatore_albo=certificatore_albo,
        zona_climatica=zona_climatica,
        epgl_nren=epgl_nren,
        superficie_utile_mq=superficie_utile_mq,
        note=note,
        created_by=current_user.id,
        stato=_calc_stato(data_scadenza)
    )
    ape_id = ape.id

    # Salvataggio file con prefisso ape_id per evitare conflitti
    safe_filename = f"{ape_id}_{file.filename}"
    file_path = storage_dir / safe_filename
    async with aiofiles.open(file_path, "wb") as f:
        await f.write(content)

    ape.file_path = str(file_path)
    ape.file_name = file.filename
    ape.file_mime = file.content_type
    ape.file_size_bytes = len(content)

    # Marca APE precedenti come sostituiti
    await db.ape.update_many(
        {"unita_id": unita_id, "stato": {"$ne": StatoApe.SOSTITUITO.value}},
        {"$set": {"stato": StatoApe.SOSTITUITO.value, "updated_at": datetime.now(timezone.utc).isoformat()}}
    )

    doc = _serialize_ape_for_db(ape)
    await db.ape.insert_one(doc)
    doc.pop("_id", None)
    await log_audit(db, "ape", ape.id, "create", None, doc, current_user.id)

    return await _enrich_ape(db, doc)


@router.put("/{ape_id}")
async def update_ape(
    ape_id: str,
    data: ApeUpdate,
    current_user: UserInDB = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """Aggiorna campi APE (esclusi file e scadenza tramite endpoint dedicati)."""
    if current_user.ruolo == UserRole.LETTURA:
        raise HTTPException(status_code=403, detail="Permessi insufficienti")

    existing = await db.ape.find_one({"id": ape_id}, {"_id": 0})
    if not existing:
        raise HTTPException(status_code=404, detail="APE non trovato")

    update_data = {k: v for k, v in data.model_dump(exclude_unset=True).items() if v is not None}
    # Serializza date
    for date_field in ("data_emissione", "data_scadenza"):
        if date_field in update_data and isinstance(update_data[date_field], date):
            update_data[date_field] = update_data[date_field].isoformat()
    if "classe_energetica" in update_data and hasattr(update_data["classe_energetica"], "value"):
        update_data["classe_energetica"] = update_data["classe_energetica"].value
    if "zona_climatica" in update_data and hasattr(update_data["zona_climatica"], "value"):
        update_data["zona_climatica"] = update_data["zona_climatica"].value

    update_data["updated_at"] = datetime.now(timezone.utc).isoformat()

    # Ricalcola stato se cambia scadenza
    if "data_scadenza" in update_data:
        try:
            sc = date.fromisoformat(update_data["data_scadenza"])
            update_data["stato"] = _calc_stato(sc).value
        except (ValueError, TypeError):
            pass

    await db.ape.update_one({"id": ape_id}, {"$set": update_data})
    await log_audit(db, "ape", ape_id, "update", existing, update_data, current_user.id)

    new_doc = await db.ape.find_one({"id": ape_id}, {"_id": 0})
    return await _enrich_ape(db, new_doc)


@router.put("/{ape_id}/scadenza")
async def rimanda_scadenza(
    ape_id: str,
    payload: RimandoScadenzaInput,
    current_user: UserInDB = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """Rimanda/modifica la data di scadenza di un APE con motivazione tracciata."""
    if current_user.ruolo == UserRole.LETTURA:
        raise HTTPException(status_code=403, detail="Permessi insufficienti")

    existing = await db.ape.find_one({"id": ape_id}, {"_id": 0})
    if not existing:
        raise HTTPException(status_code=404, detail="APE non trovato")

    old_scadenza = existing.get("data_scadenza")
    new_scadenza = payload.nuova_scadenza.isoformat()

    storico_entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "user_id": current_user.id,
        "user_nome": current_user.nome,
        "azione": "rimando_scadenza",
        "valore_precedente": old_scadenza,
        "valore_nuovo": new_scadenza,
        "motivazione": payload.motivazione
    }

    nuovo_stato = _calc_stato(payload.nuova_scadenza).value

    await db.ape.update_one(
        {"id": ape_id},
        {
            "$set": {
                "data_scadenza": new_scadenza,
                "stato": nuovo_stato,
                "updated_at": datetime.now(timezone.utc).isoformat()
            },
            "$push": {"storico_modifiche": storico_entry}
        }
    )
    await log_audit(
        db, "ape", ape_id, "rimando_scadenza",
        {"data_scadenza": old_scadenza},
        {"data_scadenza": new_scadenza, "motivazione": payload.motivazione},
        current_user.id
    )

    new_doc = await db.ape.find_one({"id": ape_id}, {"_id": 0})
    return await _enrich_ape(db, new_doc)


@router.put("/{ape_id}/file")
async def replace_ape_file(
    ape_id: str,
    file: UploadFile = File(...),
    motivazione: str = Form(...),
    current_user: UserInDB = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """Sostituisce il file PDF dell'APE mantenendo lo stesso record."""
    if current_user.ruolo == UserRole.LETTURA:
        raise HTTPException(status_code=403, detail="Permessi insufficienti")

    existing = await db.ape.find_one({"id": ape_id}, {"_id": 0})
    if not existing:
        raise HTTPException(status_code=404, detail="APE non trovato")

    if file.content_type not in ALLOWED_MIMES:
        raise HTTPException(status_code=400, detail="Tipo file non supportato. Ammessi: PDF, PNG, JPEG")

    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail=f"File troppo grande. Max {MAX_FILE_SIZE // 1024 // 1024}MB")

    # Rimuovi vecchio file se presente
    if existing.get("file_path") and os.path.exists(existing["file_path"]):
        try:
            os.remove(existing["file_path"])
        except OSError:
            pass

    storage_dir = APE_DIR / existing["unita_id"]
    storage_dir.mkdir(parents=True, exist_ok=True)
    safe_filename = f"{ape_id}_{file.filename}"
    file_path = storage_dir / safe_filename
    async with aiofiles.open(file_path, "wb") as f:
        await f.write(content)

    storico_entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "user_id": current_user.id,
        "user_nome": current_user.nome,
        "azione": "sostituzione_file",
        "valore_precedente": existing.get("file_name"),
        "valore_nuovo": file.filename,
        "motivazione": motivazione
    }

    await db.ape.update_one(
        {"id": ape_id},
        {
            "$set": {
                "file_path": str(file_path),
                "file_name": file.filename,
                "file_mime": file.content_type,
                "file_size_bytes": len(content),
                "updated_at": datetime.now(timezone.utc).isoformat()
            },
            "$push": {"storico_modifiche": storico_entry}
        }
    )
    await log_audit(
        db, "ape", ape_id, "replace_file",
        {"file_name": existing.get("file_name")},
        {"file_name": file.filename, "motivazione": motivazione},
        current_user.id
    )

    new_doc = await db.ape.find_one({"id": ape_id}, {"_id": 0})
    return await _enrich_ape(db, new_doc)


@router.delete("/{ape_id}")
async def delete_ape(
    ape_id: str,
    current_user: UserInDB = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """Elimina APE (e file associato)."""
    if current_user.ruolo == UserRole.LETTURA:
        raise HTTPException(status_code=403, detail="Permessi insufficienti")

    existing = await db.ape.find_one({"id": ape_id}, {"_id": 0})
    if not existing:
        raise HTTPException(status_code=404, detail="APE non trovato")

    if existing.get("file_path") and os.path.exists(existing["file_path"]):
        try:
            os.remove(existing["file_path"])
        except OSError:
            pass

    await db.ape.delete_one({"id": ape_id})
    await log_audit(db, "ape", ape_id, "delete", existing, None, current_user.id)
    return {"message": "APE eliminato"}


@router.get("/stats/dashboard")
async def ape_stats(
    current_user: UserInDB = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """Statistiche APE per dashboard."""
    today_iso = _today().isoformat()
    in_scadenza_target = (_today() + timedelta(days=90)).isoformat()

    total = await db.ape.count_documents({"stato": {"$ne": StatoApe.SOSTITUITO.value}})
    scaduti = await db.ape.count_documents({"data_scadenza": {"$lt": today_iso}, "stato": {"$ne": StatoApe.SOSTITUITO.value}})
    in_scadenza = await db.ape.count_documents({
        "data_scadenza": {"$gte": today_iso, "$lte": in_scadenza_target},
        "stato": {"$ne": StatoApe.SOSTITUITO.value}
    })
    validi = total - scaduti - in_scadenza

    # Distribuzione classi energetiche (solo APE attivi)
    by_classe = {}
    for c in [c.value for c in ClasseEnergetica]:
        by_classe[c] = await db.ape.count_documents({
            "classe_energetica": c,
            "stato": {"$ne": StatoApe.SOSTITUITO.value}
        })

    return {
        "total": total,
        "validi": max(0, validi),
        "in_scadenza": in_scadenza,
        "scaduti": scaduti,
        "by_classe": by_classe
    }
