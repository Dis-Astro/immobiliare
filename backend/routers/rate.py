from fastapi import APIRouter, HTTPException, Depends, Query, UploadFile, File
from typing import List, Optional
from datetime import date, datetime, timezone
import csv, io
from motor.motor_asyncio import AsyncIOMotorDatabase

from models.rata import Rata, RataCreate, RataCreateManuale, RataUpdate, StatoRata, MetodoPagamento, ParsedBankRow, BatchCreateRate
from models.user import UserInDB, UserRole
from routers.auth import get_current_user, get_db
from services.audit import log_audit

router = APIRouter(prefix="/rate", tags=["Rate/Pagamenti"])


@router.get("", response_model=List[Rata])
async def list_rate(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    contratto_id: Optional[str] = None,
    stato: Optional[StatoRata] = None,
    periodo_da: Optional[str] = None,
    periodo_a: Optional[str] = None,
    in_ritardo: Optional[bool] = None,
    current_user: UserInDB = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """Lista rate con filtri."""
    query = {}
    if contratto_id:
        query["contratto_id"] = contratto_id
    if stato:
        query["stato"] = stato
    if periodo_da:
        query["periodo"] = {"$gte": periodo_da}
    if periodo_a:
        if "periodo" not in query:
            query["periodo"] = {}
        query["periodo"]["$lte"] = periodo_a
    if in_ritardo:
        query["stato"] = StatoRata.IN_RITARDO
    
    rate = await db.rate.find(query, {"_id": 0}).sort("data_scadenza", -1).skip(skip).limit(limit).to_list(limit)
    
    # Update ritardo status and enrich
    today = date.today()
    for r in rate:
        # Calculate delay
        if r.get("data_scadenza") and r["stato"] == StatoRata.DA_INCASSARE.value:
            scadenza = date.fromisoformat(r["data_scadenza"]) if isinstance(r["data_scadenza"], str) else r["data_scadenza"]
            if today > scadenza:
                r["giorni_ritardo"] = (today - scadenza).days
                r["stato"] = StatoRata.IN_RITARDO.value
                # Update in DB
                await db.rate.update_one(
                    {"id": r["id"]},
                    {"$set": {"stato": StatoRata.IN_RITARDO.value, "giorni_ritardo": r["giorni_ritardo"]}}
                )
        
        # Enrich with contract/tenant info
        contratto = await db.contratti.find_one({"id": r["contratto_id"]}, {"_id": 0})
        if contratto:
            r["contratto_codice"] = contratto.get("codice_contratto")
            affittuario = await db.soggetti.find_one({"id": contratto["affittuario_id"]}, {"nome": 1})
            r["affittuario_nome"] = affittuario["nome"] if affittuario else None
            
            unita = await db.unita.find_one({"id": contratto["unita_id"]}, {"immobile_id": 1})
            if unita:
                immobile = await db.immobili.find_one({"id": unita["immobile_id"]}, {"titolo": 1})
                r["immobile_titolo"] = immobile["titolo"] if immobile else None
    
    return rate


@router.get("/in-ritardo")
async def get_rate_in_ritardo(
    limit: int = Query(20, ge=1, le=100),
    current_user: UserInDB = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """Ottieni rate in ritardo ordinate per gravità."""
    today = date.today().isoformat()
    
    rate = await db.rate.find({
        "stato": {"$in": [StatoRata.DA_INCASSARE.value, StatoRata.IN_RITARDO.value]},
        "data_scadenza": {"$lt": today}
    }, {"_id": 0}).sort("data_scadenza", 1).limit(limit).to_list(limit)
    
    # Enrich
    for r in rate:
        scadenza = date.fromisoformat(r["data_scadenza"]) if isinstance(r["data_scadenza"], str) else r["data_scadenza"]
        r["giorni_ritardo"] = (date.today() - scadenza).days
        
        contratto = await db.contratti.find_one({"id": r["contratto_id"]}, {"_id": 0})
        if contratto:
            r["contratto_codice"] = contratto.get("codice_contratto")
            affittuario = await db.soggetti.find_one({"id": contratto["affittuario_id"]}, {"nome": 1})
            r["affittuario_nome"] = affittuario["nome"] if affittuario else None
            
            unita = await db.unita.find_one({"id": contratto["unita_id"]}, {"immobile_id": 1})
            if unita:
                immobile = await db.immobili.find_one({"id": unita["immobile_id"]}, {"titolo": 1})
                r["immobile_titolo"] = immobile["titolo"] if immobile else None
    
    return rate


@router.get("/stats")
async def get_rate_stats(
    periodo: Optional[str] = None,  # YYYY-MM
    current_user: UserInDB = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """Statistiche rate."""
    query = {}
    if periodo:
        query["periodo"] = periodo
    else:
        # Current month
        query["periodo"] = date.today().strftime("%Y-%m")
    
    rate = await db.rate.find(query, {"_id": 0}).to_list(1000)
    
    totale = sum(r["importo"] for r in rate)
    incassato = sum(r["importo"] for r in rate if r["stato"] == StatoRata.INCASSATO.value)
    in_ritardo = sum(r["importo"] for r in rate if r["stato"] == StatoRata.IN_RITARDO.value)
    da_incassare = sum(r["importo"] for r in rate if r["stato"] == StatoRata.DA_INCASSARE.value)
    
    return {
        "periodo": query["periodo"],
        "totale": totale,
        "incassato": incassato,
        "in_ritardo": in_ritardo,
        "da_incassare": da_incassare,
        "percentuale_incassato": round(incassato / totale * 100, 1) if totale > 0 else 0
    }


@router.post("", response_model=Rata)
async def create_rata(
    data: RataCreateManuale,
    current_user: UserInDB = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """Crea manualmente una nuova rata/pagamento."""
    if current_user.ruolo == UserRole.LETTURA:
        raise HTTPException(status_code=403, detail="Permessi insufficienti")
    
    contratto = await db.contratti.find_one({"id": data.contratto_id}, {"_id": 0})
    if not contratto:
        raise HTTPException(status_code=404, detail="Contratto non trovato")
    
    rata = Rata(
        contratto_id=data.contratto_id,
        periodo=data.periodo,
        importo=data.importo,
        stato=data.stato,
        data_scadenza=data.data_scadenza,
        data_incasso=data.data_incasso,
        metodo=data.metodo,
        riferimento=data.riferimento,
        note=data.note,
    )
    rata_dict = rata.model_dump()
    rata_dict["created_at"] = rata_dict["created_at"].isoformat()
    if rata_dict.get("data_scadenza"):
        rata_dict["data_scadenza"] = rata_dict["data_scadenza"].isoformat()
    if rata_dict.get("data_incasso"):
        rata_dict["data_incasso"] = rata_dict["data_incasso"].isoformat()
    
    await db.rate.insert_one(rata_dict)
    await log_audit(db, "rate", rata.id, "create", None, rata_dict, current_user.id)
    
    return rata


@router.post("/parse-bank-statement")
async def parse_bank_statement(
    file: UploadFile = File(...),
    current_user: UserInDB = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """Analizza CSV estratto conto bancario e associa a soggetti."""
    if current_user.ruolo == UserRole.LETTURA:
        raise HTTPException(status_code=403, detail="Permessi insufficienti")
    
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="Sono ammessi solo file CSV")
    
    content = await file.read()
    text = content.decode('utf-8-sig')
    reader = csv.DictReader(io.StringIO(text))
    
    # Get all soggetti for matching
    soggetti = await db.soggetti.find({}, {"_id": 0, "id": 1, "nome": 1}).to_list(1000)
    
    rows = []
    for i, row in enumerate(reader):
        # Try to extract date, description, amount from common CSV formats
        data = row.get('data') or row.get('Data') or row.get('DATA') or ''
        descrizione = row.get('descrizione') or row.get('Descrizione') or row.get('Descrizione operazione') or row.get('operazione') or ''
        importo_str = row.get('importo') or row.get('Importo') or row.get('Importo €') or row.get('importo_euro') or ''
        segno = '+'
        
        # Parse importo
        importo = 0.0
        if importo_str:
            importo_str = importo_str.replace('€', '').replace(' ', '').replace('.', '').replace(',', '.').strip()
            try:
                importo = float(importo_str)
            except ValueError:
                pass
        
        # Negative amounts (prefixed with -)
        if importo < 0:
            segno = '-'
            importo = abs(importo)
        
        # Try to match against soggetti by name
        matched_id = None
        matched_nome = None
        best_score = 0
        for s in soggetti:
            score = 0
            nome_parts = s['nome'].lower().split()
            desc_lower = descrizione.lower()
            for part in nome_parts:
                if len(part) > 2 and part in desc_lower:
                    score += 1
            if score > best_score:
                best_score = score
                matched_id = s['id']
                matched_nome = s['nome']
        
        confidence = min(best_score * 33, 100) if best_score > 0 else 0
        
        rows.append(ParsedBankRow(
            riga=i+1,
            data=data,
            descrizione=descrizione,
            importo=importo,
            segno=segno,
            affittuario_suggerito_id=matched_id,
            affittuario_suggerito_nome=matched_nome,
            confidence=confidence
        ))
    
    return {"rows": rows, "total": len(rows)}


@router.post("/batch-create", response_model=List[Rata])
async def batch_create_rate(
    data: BatchCreateRate,
    current_user: UserInDB = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """Crea multiple rate in batch (usato dopo conferma import)."""
    if current_user.ruolo == UserRole.LETTURA:
        raise HTTPException(status_code=403, detail="Permessi insufficienti")
    
    created = []
    for rata_data in data.rate:
        contratto = await db.contratti.find_one({"id": rata_data.contratto_id}, {"_id": 0})
        if not contratto:
            continue
        
        rata = Rata(
            contratto_id=rata_data.contratto_id,
            periodo=rata_data.periodo,
            importo=rata_data.importo,
            stato=rata_data.stato,
        )
        rata_dict = rata.model_dump()
        rata_dict["created_at"] = rata_dict["created_at"].isoformat()
        rata_dict["data_scadenza"] = rata_dict["data_scadenza"].isoformat() if rata_dict.get("data_scadenza") else None
        
        await db.rate.insert_one(rata_dict)
        await log_audit(db, "rate", rata.id, "create", None, rata_dict, current_user.id)
        created.append(rata)
    
    return created


@router.put("/{rata_id}", response_model=Rata)
async def update_rata(
    rata_id: str,
    data: RataUpdate,
    current_user: UserInDB = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """Aggiorna rata (es. segna come incassata)."""
    if current_user.ruolo == UserRole.LETTURA:
        raise HTTPException(status_code=403, detail="Permessi insufficienti")
    
    existing = await db.rate.find_one({"id": rata_id}, {"_id": 0})
    if not existing:
        raise HTTPException(status_code=404, detail="Rata non trovata")
    
    update_dict = data.model_dump(exclude_unset=True)
    
    # Auto-set incasso date if marking as paid
    if update_dict.get("stato") == StatoRata.INCASSATO and "data_incasso" not in update_dict:
        update_dict["data_incasso"] = date.today().isoformat()
    
    # Convert dates
    if "data_incasso" in update_dict and update_dict["data_incasso"]:
        update_dict["data_incasso"] = update_dict["data_incasso"].isoformat() if hasattr(update_dict["data_incasso"], 'isoformat') else update_dict["data_incasso"]
    
    if update_dict:
        await db.rate.update_one({"id": rata_id}, {"$set": update_dict})
        await log_audit(db, "rate", rata_id, "update", existing, update_dict, current_user.id)
    
    updated = await db.rate.find_one({"id": rata_id}, {"_id": 0})
    return updated


@router.post("/{rata_id}/incassa")
async def incassa_rata(
    rata_id: str,
    metodo: MetodoPagamento = MetodoPagamento.BONIFICO,
    riferimento: Optional[str] = None,
    current_user: UserInDB = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """Azione rapida: segna rata come incassata."""
    if current_user.ruolo == UserRole.LETTURA:
        raise HTTPException(status_code=403, detail="Permessi insufficienti")
    
    existing = await db.rate.find_one({"id": rata_id}, {"_id": 0})
    if not existing:
        raise HTTPException(status_code=404, detail="Rata non trovata")
    
    update_dict = {
        "stato": StatoRata.INCASSATO.value,
        "data_incasso": date.today().isoformat(),
        "metodo": metodo.value,
        "riferimento": riferimento
    }
    
    await db.rate.update_one({"id": rata_id}, {"$set": update_dict})
    await log_audit(db, "rate", rata_id, "update", existing, update_dict, current_user.id)
    
    return {"message": "Rata incassata", "data_incasso": update_dict["data_incasso"]}
