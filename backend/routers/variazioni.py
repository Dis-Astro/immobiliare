from fastapi import APIRouter, HTTPException, Depends, Query
from typing import List, Optional
from motor.motor_asyncio import AsyncIOMotorDatabase

from models.variazione import VariazioneContratto, VariazioneCreate, TipoVariazione
from models.user import UserInDB, UserRole
from routers.auth import get_current_user, get_db
from services.audit import log_audit

router = APIRouter(prefix="/variazioni", tags=["Variazioni Contratto"])


@router.get("", response_model=List[VariazioneContratto])
async def list_variazioni(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    contratto_id: Optional[str] = None,
    tipo: Optional[TipoVariazione] = None,
    current_user: UserInDB = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """Lista variazioni contratto."""
    query = {}
    if contratto_id:
        query["contratto_id"] = contratto_id
    if tipo:
        query["tipo"] = tipo
    
    variazioni = await db.variazioni.find(query, {"_id": 0}).sort("data_efficacia", -1).skip(skip).limit(limit).to_list(limit)
    
    # Enrich
    for v in variazioni:
        contratto = await db.contratti.find_one({"id": v["contratto_id"]}, {"codice_contratto": 1})
        v["contratto_codice"] = contratto["codice_contratto"] if contratto else None
    
    return variazioni


@router.post("", response_model=VariazioneContratto)
async def create_variazione(
    data: VariazioneCreate,
    current_user: UserInDB = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """Crea variazione contratto."""
    if current_user.ruolo == UserRole.LETTURA:
        raise HTTPException(status_code=403, detail="Permessi insufficienti")
    
    # Get contratto
    contratto = await db.contratti.find_one({"id": data.contratto_id}, {"_id": 0})
    if not contratto:
        raise HTTPException(status_code=404, detail="Contratto non trovato")
    
    variazione = VariazioneContratto(**data.model_dump())
    variazione.created_by = current_user.id
    
    var_dict = variazione.model_dump()
    var_dict["created_at"] = var_dict["created_at"].isoformat()
    var_dict["data_efficacia"] = var_dict["data_efficacia"].isoformat()
    
    await db.variazioni.insert_one(var_dict)
    await log_audit(db, "variazioni", variazione.id, "create", None, var_dict, current_user.id)
    
    # Apply variation effects based on type
    if data.tipo == TipoVariazione.PROROGA:
        # Update contract end date
        new_values = data.diff_json.get("durata_mesi", {})
        if new_values.get("new"):
            from dateutil.relativedelta import relativedelta
            from datetime import date
            data_inizio = date.fromisoformat(contratto["data_inizio"])
            new_scadenza = data_inizio + relativedelta(months=new_values["new"])
            await db.contratti.update_one(
                {"id": data.contratto_id},
                {"$set": {
                    "durata_mesi": new_values["new"],
                    "data_scadenza": new_scadenza.isoformat()
                }}
            )
    
    elif data.tipo == TipoVariazione.RINEGOZIAZIONE:
        # Update canone if changed
        canone_change = data.diff_json.get("canone_importo", {})
        if canone_change.get("new"):
            await db.contratti.update_one(
                {"id": data.contratto_id},
                {"$set": {"canone_importo": canone_change["new"]}}
            )
            # Update future unpaid rates
            await db.rate.update_many(
                {"contratto_id": data.contratto_id, "stato": "da_incassare"},
                {"$set": {"importo": canone_change["new"]}}
            )
    
    elif data.tipo == TipoVariazione.RECESSO:
        await db.contratti.update_one(
            {"id": data.contratto_id},
            {"$set": {"stato": "chiuso"}}
        )
    
    return variazione


@router.get("/{variazione_id}", response_model=VariazioneContratto)
async def get_variazione(
    variazione_id: str,
    current_user: UserInDB = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """Ottieni dettagli variazione."""
    variazione = await db.variazioni.find_one({"id": variazione_id}, {"_id": 0})
    if not variazione:
        raise HTTPException(status_code=404, detail="Variazione non trovata")
    
    contratto = await db.contratti.find_one({"id": variazione["contratto_id"]}, {"codice_contratto": 1})
    variazione["contratto_codice"] = contratto["codice_contratto"] if contratto else None
    
    return variazione
