from fastapi import APIRouter, HTTPException, Depends, Query
from typing import List, Optional
from motor.motor_asyncio import AsyncIOMotorDatabase
from datetime import date

from models.user import UserInDB, UserRole
from routers.auth import get_current_user, get_db

router = APIRouter(prefix="/mappa", tags=["Mappa"])


@router.get("/markers")
async def get_markers(
    stato: Optional[str] = None,  # rosso, giallo, verde, grigio
    bounds: Optional[str] = None,  # sw_lat,sw_lng,ne_lat,ne_lng
    current_user: UserInDB = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """
    Ottieni marker mappa con stato colorato.
    - Rosso: ritardi >7gg, recessi contestati, eventi critici alta gravità
    - Giallo: scadenze prossime, doc in scadenza
    - Verde: tutto ok
    - Grigio: non locato
    """
    # Get all immobili with coordinates
    query = {"lat": {"$ne": None}, "lon": {"$ne": None}}
    
    # Apply bounds filter if provided
    if bounds:
        try:
            sw_lat, sw_lng, ne_lat, ne_lng = map(float, bounds.split(","))
            query["lat"] = {"$gte": sw_lat, "$lte": ne_lat}
            query["lon"] = {"$gte": sw_lng, "$lte": ne_lng}
        except:
            pass
    
    immobili = await db.immobili.find(query, {"_id": 0}).to_list(500)
    
    markers = []
    today = date.today()
    
    for imm in immobili:
        # Get units for this property
        unita_list = await db.unita.find({"immobile_id": imm["id"]}, {"_id": 0}).to_list(100)
        unita_ids = [u["id"] for u in unita_list]
        
        # Get active contracts
        contratti = await db.contratti.find({
            "unita_id": {"$in": unita_ids},
            "stato": "attivo"
        }, {"_id": 0}).to_list(100)
        
        problems = []
        status = "grigio"  # Default: not rented
        
        if contratti:
            status = "verde"  # Has contracts, assume ok
            contratto_ids = [c["id"] for c in contratti]
            
            # Check for late payments (>7 days)
            rate_ritardo = await db.rate.find({
                "contratto_id": {"$in": contratto_ids},
                "stato": "in_ritardo",
                "giorni_ritardo": {"$gt": 7}
            }, {"_id": 0}).to_list(100)
            
            if rate_ritardo:
                status = "rosso"
                problems.append(f"{len(rate_ritardo)} rate in ritardo grave")
            
            # Check for critical events (high severity)
            eventi_critici = await db.eventi_critici.count_documents({
                "unita_id": {"$in": unita_ids},
                "gravita": "alta"
            })
            
            if eventi_critici > 0:
                status = "rosso"
                problems.append(f"{eventi_critici} eventi critici")
            
            # Check contested withdrawals
            recessi_contestati = await db.recessi.count_documents({
                "contratto_id": {"$in": contratto_ids},
                "stato": "contestato"
            })
            
            if recessi_contestati > 0:
                status = "rosso"
                problems.append(f"{recessi_contestati} recessi contestati")
            
            # Check expiring contracts (within 30 days) - yellow if no red
            if status != "rosso":
                from dateutil.relativedelta import relativedelta
                target_date = (today + relativedelta(days=30)).isoformat()
                contratti_scadenza = [c for c in contratti if c.get("data_scadenza") and c["data_scadenza"] <= target_date]
                
                if contratti_scadenza:
                    status = "giallo"
                    problems.append(f"{len(contratti_scadenza)} contratti in scadenza")
            
            # Check expiring documents - yellow if no red
            if status != "rosso":
                from dateutil.relativedelta import relativedelta
                doc_target = (today + relativedelta(days=30)).isoformat()
                docs_scadenza = await db.documenti.count_documents({
                    "ref_id": {"$in": unita_ids + contratto_ids + [imm["id"]]},
                    "expiry_date": {"$lte": doc_target, "$gte": today.isoformat()}
                })
                
                if docs_scadenza > 0:
                    if status != "giallo":
                        status = "giallo"
                    problems.append(f"{docs_scadenza} documenti in scadenza")
            
            # Get tenant info for tooltip
            affittuario_nomi = []
            for c in contratti[:3]:  # Max 3
                aff = await db.soggetti.find_one({"id": c["affittuario_id"]}, {"nome": 1})
                if aff:
                    affittuario_nomi.append(aff["nome"])
        
        else:
            # No contracts
            affittuario_nomi = []
        
        # Filter by status if requested
        if stato and status != stato:
            continue
        
        markers.append({
            "id": imm["id"],
            "lat": imm["lat"],
            "lon": imm["lon"],
            "status": status,
            "tooltip": imm["titolo"],
            "problems": problems,
            "immobile": {
                "codice": imm["codice"],
                "titolo": imm["titolo"],
                "indirizzo": imm["indirizzo"],
                "foto_url": imm.get("foto_url"),
                "affittuari": affittuario_nomi,
                "unita_count": len(unita_list),
                "contratti_attivi": len(contratti)
            },
            "link": f"/immobili/{imm['id']}"
        })
    
    return {
        "markers": markers,
        "totale": len(markers),
        "by_status": {
            "rosso": len([m for m in markers if m["status"] == "rosso"]),
            "giallo": len([m for m in markers if m["status"] == "giallo"]),
            "verde": len([m for m in markers if m["status"] == "verde"]),
            "grigio": len([m for m in markers if m["status"] == "grigio"])
        }
    }


@router.get("/bounds")
async def get_bounds(
    current_user: UserInDB = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """Ottieni bounds per tutti gli immobili con coordinate."""
    immobili = await db.immobili.find(
        {"lat": {"$ne": None}, "lon": {"$ne": None}},
        {"lat": 1, "lon": 1}
    ).to_list(1000)
    
    if not immobili:
        # Default to Italy center
        return {
            "sw": {"lat": 36.0, "lng": 6.0},
            "ne": {"lat": 47.5, "lng": 19.0},
            "center": {"lat": 41.9, "lng": 12.5}
        }
    
    lats = [i["lat"] for i in immobili]
    lons = [i["lon"] for i in immobili]
    
    return {
        "sw": {"lat": min(lats), "lng": min(lons)},
        "ne": {"lat": max(lats), "lng": max(lons)},
        "center": {"lat": sum(lats) / len(lats), "lng": sum(lons) / len(lons)}
    }
