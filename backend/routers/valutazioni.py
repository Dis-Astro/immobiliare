from fastapi import APIRouter, HTTPException, Depends, Query
from typing import List, Optional
from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorDatabase

from models.valutazione import (
    ValutazioneAffittuario, ValutazioneCreate, 
    EventoCritico, EventoCriticoCreate, GravitaEvento, TipoEventoCritico
)
from models.user import UserInDB, UserRole
from routers.auth import get_current_user, get_db
from services.audit import log_audit

router = APIRouter(prefix="/valutazioni", tags=["Valutazioni"])


@router.get("", response_model=List[ValutazioneAffittuario])
async def list_valutazioni(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    affittuario_id: Optional[str] = None,
    contratto_id: Optional[str] = None,
    current_user: UserInDB = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """Lista valutazioni."""
    query = {}
    if affittuario_id:
        query["affittuario_id"] = affittuario_id
    if contratto_id:
        query["contratto_id"] = contratto_id
    
    valutazioni = await db.valutazioni_affittuari.find(query, {"_id": 0}).sort("created_at", -1).skip(skip).limit(limit).to_list(limit)
    return valutazioni


@router.get("/affittuario/{affittuario_id}/score")
async def get_affittuario_score(
    affittuario_id: str,
    current_user: UserInDB = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """Calcola score complessivo affittuario."""
    # Get all ratings
    valutazioni = await db.valutazioni_affittuari.find(
        {"affittuario_id": affittuario_id},
        {"_id": 0}
    ).to_list(100)
    
    # Get payment history
    contratti = await db.contratti.find({"affittuario_id": affittuario_id}, {"id": 1}).to_list(100)
    contratto_ids = [c["id"] for c in contratti]
    
    rate = await db.rate.find({"contratto_id": {"$in": contratto_ids}}, {"_id": 0}).to_list(1000)
    
    # Calculate payment metrics
    totale_rate = len(rate)
    rate_pagate = len([r for r in rate if r.get("stato") == "incassato"])
    rate_ritardo = len([r for r in rate if r.get("stato") == "in_ritardo"])
    insoluti = len([r for r in rate if r.get("stato") in ["da_incassare", "in_ritardo"] and r.get("giorni_ritardo", 0) > 30])
    
    ritardo_medio = 0
    if rate_ritardo > 0:
        ritardi = [r.get("giorni_ritardo", 0) for r in rate if r.get("giorni_ritardo", 0) > 0]
        ritardo_medio = sum(ritardi) / len(ritardi) if ritardi else 0
    
    percent_puntualita = (rate_pagate / totale_rate * 100) if totale_rate > 0 else 100
    
    # Payment score (0-100)
    score_pagamenti = 100
    score_pagamenti -= min(rate_ritardo * 5, 30)  # -5 per ogni ritardo, max -30
    score_pagamenti -= min(insoluti * 15, 40)  # -15 per ogni insoluto, max -40
    score_pagamenti -= min(ritardo_medio * 0.5, 30)  # -0.5 per ogni giorno medio ritardo, max -30
    score_pagamenti = max(0, score_pagamenti)
    
    # Average manual ratings
    avg_ratings = {}
    for field in ["rating_serieta", "rating_comunicazione", "rating_rispetto_immobile", "rating_vicinato"]:
        values = [v.get(field) for v in valutazioni if v.get(field)]
        avg_ratings[field] = round(sum(values) / len(values), 1) if values else None
    
    # Overall rating (1-5 stars)
    manual_scores = [v for v in avg_ratings.values() if v]
    overall_rating = round(sum(manual_scores) / len(manual_scores), 1) if manual_scores else None
    
    # Get critical events count
    eventi_critici = await db.eventi_critici.count_documents({"affittuario_id": affittuario_id})
    eventi_alta_gravita = await db.eventi_critici.count_documents({
        "affittuario_id": affittuario_id,
        "gravita": "alta"
    })
    
    # Final reputation tag
    if score_pagamenti >= 90 and (overall_rating is None or overall_rating >= 4) and eventi_alta_gravita == 0:
        tag = "Affidabile"
        color = "green"
    elif score_pagamenti >= 70 and eventi_alta_gravita == 0:
        tag = "Nella media"
        color = "yellow"
    elif score_pagamenti < 50 or eventi_alta_gravita > 0:
        tag = "Critico"
        color = "red"
    else:
        tag = "Da monitorare"
        color = "orange"
    
    return {
        "affittuario_id": affittuario_id,
        "score_pagamenti": round(score_pagamenti),
        "percent_puntualita": round(percent_puntualita, 1),
        "ritardo_medio_giorni": round(ritardo_medio, 1),
        "insoluti_num": insoluti,
        "totale_rate": totale_rate,
        "rate_pagate": rate_pagate,
        "ratings": avg_ratings,
        "overall_rating": overall_rating,
        "eventi_critici": eventi_critici,
        "eventi_alta_gravita": eventi_alta_gravita,
        "tag": tag,
        "tag_color": color
    }


@router.post("", response_model=ValutazioneAffittuario)
async def create_valutazione(
    data: ValutazioneCreate,
    current_user: UserInDB = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """Crea valutazione affittuario."""
    if current_user.ruolo == UserRole.LETTURA:
        raise HTTPException(status_code=403, detail="Permessi insufficienti")
    
    # Check affittuario exists
    affittuario = await db.soggetti.find_one({"id": data.affittuario_id})
    if not affittuario:
        raise HTTPException(status_code=404, detail="Affittuario non trovato")
    
    valutazione = ValutazioneAffittuario(**data.model_dump())
    valutazione.created_by = current_user.id
    
    val_dict = valutazione.model_dump()
    val_dict["created_at"] = val_dict["created_at"].isoformat()
    
    await db.valutazioni_affittuari.insert_one(val_dict)
    await log_audit(db, "valutazioni_affittuari", valutazione.id, "create", None, val_dict, current_user.id)
    
    return valutazione


# Eventi Critici
@router.get("/eventi-critici", response_model=List[EventoCritico])
async def list_eventi_critici(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    affittuario_id: Optional[str] = None,
    gravita: Optional[GravitaEvento] = None,
    tipo: Optional[TipoEventoCritico] = None,
    current_user: UserInDB = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """Lista eventi critici."""
    query = {}
    if affittuario_id:
        query["affittuario_id"] = affittuario_id
    if gravita:
        query["gravita"] = gravita
    if tipo:
        query["tipo"] = tipo
    
    eventi = await db.eventi_critici.find(query, {"_id": 0}).sort("data_evento", -1).skip(skip).limit(limit).to_list(limit)
    
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


@router.post("/eventi-critici", response_model=EventoCritico)
async def create_evento_critico(
    data: EventoCriticoCreate,
    current_user: UserInDB = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """Registra evento critico."""
    if current_user.ruolo == UserRole.LETTURA:
        raise HTTPException(status_code=403, detail="Permessi insufficienti")
    
    evento = EventoCritico(**data.model_dump())
    evento.created_by = current_user.id
    
    evento_dict = evento.model_dump()
    evento_dict["created_at"] = evento_dict["created_at"].isoformat()
    evento_dict["data_evento"] = evento_dict["data_evento"].isoformat()
    
    await db.eventi_critici.insert_one(evento_dict)
    await log_audit(db, "eventi_critici", evento.id, "create", None, evento_dict, current_user.id)
    
    # Send notification if high severity
    if data.gravita == GravitaEvento.ALTA:
        from services.notifications import create_evento_critico_notification
        await create_evento_critico_notification(db, evento)
    
    return evento
