from fastapi import APIRouter, HTTPException, Depends, Query
from typing import List, Optional
from motor.motor_asyncio import AsyncIOMotorDatabase

from models.immobile import Immobile, ImmobileCreate, ImmobileUpdate
from models.user import UserInDB, UserRole
from routers.auth import get_current_user, get_db
from services.audit import log_audit
from utils.geocoding import geocode_address

router = APIRouter(prefix="/immobili", tags=["Immobili"])


@router.get("", response_model=List[Immobile])
async def list_immobili(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    search: Optional[str] = None,
    has_coords: Optional[bool] = None,
    current_user: UserInDB = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """Lista immobili con filtri."""
    query = {}
    if search:
        query["$or"] = [
            {"codice": {"$regex": search, "$options": "i"}},
            {"titolo": {"$regex": search, "$options": "i"}},
            {"indirizzo": {"$regex": search, "$options": "i"}}
        ]
    if has_coords is not None:
        if has_coords:
            query["lat"] = {"$ne": None}
            query["lon"] = {"$ne": None}
        else:
            query["$or"] = [{"lat": None}, {"lon": None}]
    
    immobili = await db.immobili.find(query, {"_id": 0}).skip(skip).limit(limit).to_list(limit)
    
    # Enrich with unit count and active contracts
    for imm in immobili:
        imm["unita_count"] = await db.unita.count_documents({"immobile_id": imm["id"]})
        imm["contratti_attivi"] = await db.contratti.count_documents({
            "stato": "attivo",
            "unita_id": {"$in": [u["id"] async for u in db.unita.find({"immobile_id": imm["id"]}, {"id": 1})]}
        })
    
    return immobili


@router.get("/count")
async def count_immobili(
    current_user: UserInDB = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """Conta immobili."""
    count = await db.immobili.count_documents({})
    return {"count": count}


@router.post("", response_model=Immobile)
async def create_immobile(
    data: ImmobileCreate,
    current_user: UserInDB = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """Crea nuovo immobile."""
    if current_user.ruolo == UserRole.LETTURA:
        raise HTTPException(status_code=403, detail="Permessi insufficienti")
    
    # Check codice unique
    existing = await db.immobili.find_one({"codice": data.codice})
    if existing:
        raise HTTPException(status_code=400, detail="Codice immobile già esistente")
    
    immobile = Immobile(**data.model_dump())
    
    # Geocode if no coords provided
    if not immobile.lat or not immobile.lon:
        result = await geocode_address(data.indirizzo)
        if result:
            immobile.lat, immobile.lon, immobile.geo_accuracy = result
    
    immobile_dict = immobile.model_dump()
    immobile_dict["created_at"] = immobile_dict["created_at"].isoformat()
    
    await db.immobili.insert_one(immobile_dict)
    await log_audit(db, "immobili", immobile.id, "create", None, immobile_dict, current_user.id)
    
    return immobile


@router.get("/{immobile_id}", response_model=Immobile)
async def get_immobile(
    immobile_id: str,
    current_user: UserInDB = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """Ottieni dettagli immobile."""
    immobile = await db.immobili.find_one({"id": immobile_id}, {"_id": 0})
    if not immobile:
        raise HTTPException(status_code=404, detail="Immobile non trovato")
    
    # Enrich
    immobile["unita_count"] = await db.unita.count_documents({"immobile_id": immobile_id})
    
    unita_ids = [u["id"] async for u in db.unita.find({"immobile_id": immobile_id}, {"id": 1})]
    immobile["contratti_attivi"] = await db.contratti.count_documents({
        "stato": "attivo",
        "unita_id": {"$in": unita_ids}
    })
    
    return immobile


@router.put("/{immobile_id}", response_model=Immobile)
async def update_immobile(
    immobile_id: str,
    data: ImmobileUpdate,
    current_user: UserInDB = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """Aggiorna immobile."""
    if current_user.ruolo == UserRole.LETTURA:
        raise HTTPException(status_code=403, detail="Permessi insufficienti")
    
    existing = await db.immobili.find_one({"id": immobile_id}, {"_id": 0})
    if not existing:
        raise HTTPException(status_code=404, detail="Immobile non trovato")
    
    update_dict = data.model_dump(exclude_unset=True)
    
    # Geocode if address changed and no coords
    if "indirizzo" in update_dict and ("lat" not in update_dict or "lon" not in update_dict):
        result = await geocode_address(update_dict["indirizzo"])
        if result:
            update_dict["lat"], update_dict["lon"], update_dict["geo_accuracy"] = result
    
    if update_dict:
        await db.immobili.update_one({"id": immobile_id}, {"$set": update_dict})
        await log_audit(db, "immobili", immobile_id, "update", existing, update_dict, current_user.id)
    
    updated = await db.immobili.find_one({"id": immobile_id}, {"_id": 0})
    return updated


@router.delete("/{immobile_id}")
async def delete_immobile(
    immobile_id: str,
    current_user: UserInDB = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """Elimina immobile (solo se non ha unità)."""
    if current_user.ruolo != UserRole.SUPERVISORE:
        raise HTTPException(status_code=403, detail="Solo supervisore può eliminare immobili")
    
    unita_count = await db.unita.count_documents({"immobile_id": immobile_id})
    if unita_count > 0:
        raise HTTPException(
            status_code=400,
            detail=f"Impossibile eliminare: {unita_count} unità collegate"
        )
    
    existing = await db.immobili.find_one({"id": immobile_id}, {"_id": 0})
    if not existing:
        raise HTTPException(status_code=404, detail="Immobile non trovato")
    
    await db.immobili.delete_one({"id": immobile_id})
    await log_audit(db, "immobili", immobile_id, "delete", existing, None, current_user.id)
    
    return {"message": "Immobile eliminato"}


@router.post("/{immobile_id}/geocode")
async def geocode_immobile(
    immobile_id: str,
    current_user: UserInDB = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """Geocodifica indirizzo immobile."""
    if current_user.ruolo == UserRole.LETTURA:
        raise HTTPException(status_code=403, detail="Permessi insufficienti")
    
    immobile = await db.immobili.find_one({"id": immobile_id}, {"_id": 0})
    if not immobile:
        raise HTTPException(status_code=404, detail="Immobile non trovato")
    
    result = await geocode_address(immobile["indirizzo"])
    if not result:
        raise HTTPException(status_code=400, detail="Impossibile geocodificare l'indirizzo")
    
    lat, lon, accuracy = result
    await db.immobili.update_one(
        {"id": immobile_id},
        {"$set": {"lat": lat, "lon": lon, "geo_accuracy": accuracy}}
    )
    
    return {"lat": lat, "lon": lon, "accuracy": accuracy}
