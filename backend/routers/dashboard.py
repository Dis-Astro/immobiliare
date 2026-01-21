from fastapi import APIRouter, HTTPException, Depends
from typing import Optional
from datetime import date, datetime, timezone
from motor.motor_asyncio import AsyncIOMotorDatabase
from dateutil.relativedelta import relativedelta

from models.user import UserInDB, UserRole
from routers.auth import get_current_user, get_db

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/overview")
async def get_dashboard_overview(
    current_user: UserInDB = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """Dashboard overview - problemi-first."""
    today = date.today()
    current_month = today.strftime("%Y-%m")
    
    # KPIs
    totale_immobili = await db.immobili.count_documents({})
    totale_unita = await db.unita.count_documents({})
    contratti_attivi = await db.contratti.count_documents({"stato": "attivo"})
    
    # Calculate units with active contracts
    contratti = await db.contratti.find({"stato": "attivo"}, {"unita_id": 1}).to_list(10000)
    unita_locate = len(set(c["unita_id"] for c in contratti))
    unita_vuote = totale_unita - unita_locate
    
    # Current month income
    rate_mese = await db.rate.find({"periodo": current_month}, {"_id": 0}).to_list(1000)
    incassi_mese = sum(r["importo"] for r in rate_mese if r["stato"] == "incassato")
    atteso_mese = sum(r["importo"] for r in rate_mese)
    
    # Late payments count
    rate_ritardo = await db.rate.count_documents({"stato": "in_ritardo"})
    insoluti_totale = await db.rate.aggregate([
        {"$match": {"stato": "in_ritardo"}},
        {"$group": {"_id": None, "total": {"$sum": "$importo"}}}
    ]).to_list(1)
    insoluti_importo = insoluti_totale[0]["total"] if insoluti_totale else 0
    
    # Expiring contracts (30 days)
    target_30 = (today + relativedelta(days=30)).isoformat()
    contratti_scadenza = await db.contratti.count_documents({
        "stato": "attivo",
        "data_scadenza": {"$lte": target_30}
    })
    
    # Recent critical events
    eventi_recenti = await db.eventi_critici.count_documents({
        "created_at": {"$gte": (today - relativedelta(days=7)).isoformat()}
    })
    
    return {
        "kpi": {
            "immobili": totale_immobili,
            "unita_totali": totale_unita,
            "unita_locate": unita_locate,
            "unita_vuote": unita_vuote,
            "contratti_attivi": contratti_attivi,
            "incassi_mese": incassi_mese,
            "atteso_mese": atteso_mese,
            "rate_in_ritardo": rate_ritardo,
            "insoluti_importo": insoluti_importo,
            "contratti_in_scadenza": contratti_scadenza,
            "eventi_critici_settimana": eventi_recenti
        }
    }


@router.get("/rate-ritardo")
async def get_rate_ritardo(
    limit: int = 10,
    current_user: UserInDB = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """Lista rate in ritardo ordinate per gravità."""
    today = date.today().isoformat()
    
    # Find late payments
    rate = await db.rate.find({
        "$or": [
            {"stato": "in_ritardo"},
            {"stato": "da_incassare", "data_scadenza": {"$lt": today}}
        ]
    }, {"_id": 0}).sort("data_scadenza", 1).limit(limit).to_list(limit)
    
    # Enrich and calculate delay
    for r in rate:
        if r.get("data_scadenza"):
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


@router.get("/eventi-critici")
async def get_eventi_critici_recenti(
    limit: int = 10,
    current_user: UserInDB = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """Lista eventi critici recenti."""
    eventi = await db.eventi_critici.find({}, {"_id": 0}).sort("data_evento", -1).limit(limit).to_list(limit)
    
    # Enrich
    for e in eventi:
        affittuario = await db.soggetti.find_one({"id": e["affittuario_id"]}, {"nome": 1})
        e["affittuario_nome"] = affittuario["nome"] if affittuario else None
        
        if e.get("unita_id"):
            unita = await db.unita.find_one({"id": e["unita_id"]}, {"codice_unita": 1, "immobile_id": 1})
            if unita:
                e["unita_codice"] = unita["codice_unita"]
                immobile = await db.immobili.find_one({"id": unita["immobile_id"]}, {"titolo": 1})
                e["immobile_titolo"] = immobile["titolo"] if immobile else None
    
    return eventi


@router.get("/contratti-scadenza")
async def get_contratti_in_scadenza(
    giorni: int = 30,
    limit: int = 10,
    current_user: UserInDB = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """Lista contratti in scadenza."""
    target = (date.today() + relativedelta(days=giorni)).isoformat()
    today = date.today().isoformat()
    
    contratti = await db.contratti.find({
        "stato": "attivo",
        "data_scadenza": {"$gte": today, "$lte": target}
    }, {"_id": 0}).sort("data_scadenza", 1).limit(limit).to_list(limit)
    
    # Enrich
    for c in contratti:
        affittuario = await db.soggetti.find_one({"id": c["affittuario_id"]}, {"nome": 1})
        c["affittuario_nome"] = affittuario["nome"] if affittuario else None
        
        unita = await db.unita.find_one({"id": c["unita_id"]}, {"codice_unita": 1, "immobile_id": 1})
        if unita:
            c["unita_codice"] = unita["codice_unita"]
            immobile = await db.immobili.find_one({"id": unita["immobile_id"]}, {"titolo": 1})
            c["immobile_titolo"] = immobile["titolo"] if immobile else None
        
        # Days until expiry
        if c.get("data_scadenza"):
            scadenza = date.fromisoformat(c["data_scadenza"]) if isinstance(c["data_scadenza"], str) else c["data_scadenza"]
            c["giorni_alla_scadenza"] = (scadenza - date.today()).days
    
    return contratti


@router.get("/documenti-scadenza")
async def get_documenti_in_scadenza(
    giorni: int = 30,
    limit: int = 10,
    current_user: UserInDB = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """Lista documenti in scadenza."""
    target = (date.today() + relativedelta(days=giorni)).isoformat()
    today = date.today().isoformat()
    
    documenti = await db.documenti.find({
        "expiry_date": {"$gte": today, "$lte": target}
    }, {"_id": 0}).sort("expiry_date", 1).limit(limit).to_list(limit)
    
    return documenti
