from fastapi import APIRouter, HTTPException, Depends, Query
from typing import List, Optional
from motor.motor_asyncio import AsyncIOMotorDatabase

from models.spesa import SpesaImmobile, SpesaCreate, CategoriaSpesa, ImputabileA
from models.user import UserInDB, UserRole
from routers.auth import get_current_user, get_db
from services.audit import log_audit

router = APIRouter(prefix="/spese", tags=["Spese"])


@router.get("", response_model=List[SpesaImmobile])
async def list_spese(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    immobile_id: Optional[str] = None,
    unita_id: Optional[str] = None,
    categoria: Optional[CategoriaSpesa] = None,
    imputabile_a: Optional[ImputabileA] = None,
    anno: Optional[int] = None,
    current_user: UserInDB = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """Lista spese con filtri."""
    query = {}
    if immobile_id:
        query["immobile_id"] = immobile_id
    if unita_id:
        query["unita_id"] = unita_id
    if categoria:
        query["categoria"] = categoria
    if imputabile_a:
        query["imputabile_a"] = imputabile_a
    if anno:
        query["data"] = {"$regex": f"^{anno}"}
    
    spese = await db.spese.find(query, {"_id": 0}).sort("data", -1).skip(skip).limit(limit).to_list(limit)
    
    # Enrich
    for s in spese:
        immobile = await db.immobili.find_one({"id": s["immobile_id"]}, {"titolo": 1})
        s["immobile_titolo"] = immobile["titolo"] if immobile else None
        
        if s.get("unita_id"):
            unita = await db.unita.find_one({"id": s["unita_id"]}, {"codice_unita": 1})
            s["unita_codice"] = unita["codice_unita"] if unita else None
    
    return spese


@router.get("/stats")
async def get_spese_stats(
    anno: Optional[int] = None,
    immobile_id: Optional[str] = None,
    current_user: UserInDB = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """Statistiche spese."""
    from datetime import date
    
    if not anno:
        anno = date.today().year
    
    query = {"data": {"$regex": f"^{anno}"}}
    if immobile_id:
        query["immobile_id"] = immobile_id
    
    spese = await db.spese.find(query, {"_id": 0}).to_list(1000)
    
    totale = sum(s["importo"] for s in spese)
    
    # By categoria
    by_categoria = {}
    for s in spese:
        cat = s["categoria"]
        by_categoria[cat] = by_categoria.get(cat, 0) + s["importo"]
    
    # By imputabile_a
    by_imputabile = {}
    for s in spese:
        imp = s["imputabile_a"]
        by_imputabile[imp] = by_imputabile.get(imp, 0) + s["importo"]
    
    # By month
    by_mese = {}
    for s in spese:
        mese = s["data"][:7]  # YYYY-MM
        by_mese[mese] = by_mese.get(mese, 0) + s["importo"]
    
    return {
        "anno": anno,
        "totale": totale,
        "by_categoria": by_categoria,
        "by_imputabile": by_imputabile,
        "by_mese": dict(sorted(by_mese.items()))
    }


@router.post("", response_model=SpesaImmobile)
async def create_spesa(
    data: SpesaCreate,
    current_user: UserInDB = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """Registra spesa."""
    if current_user.ruolo == UserRole.LETTURA:
        raise HTTPException(status_code=403, detail="Permessi insufficienti")
    
    # Validate immobile
    immobile = await db.immobili.find_one({"id": data.immobile_id})
    if not immobile:
        raise HTTPException(status_code=404, detail="Immobile non trovato")
    
    spesa = SpesaImmobile(**data.model_dump())
    spesa.created_by = current_user.id
    
    spesa_dict = spesa.model_dump()
    spesa_dict["created_at"] = spesa_dict["created_at"].isoformat()
    spesa_dict["data"] = spesa_dict["data"].isoformat()
    
    await db.spese.insert_one(spesa_dict)
    await log_audit(db, "spese", spesa.id, "create", None, spesa_dict, current_user.id)
    
    return spesa


@router.get("/{spesa_id}", response_model=SpesaImmobile)
async def get_spesa(
    spesa_id: str,
    current_user: UserInDB = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """Ottieni dettagli spesa."""
    spesa = await db.spese.find_one({"id": spesa_id}, {"_id": 0})
    if not spesa:
        raise HTTPException(status_code=404, detail="Spesa non trovata")
    return spesa


@router.put("/{spesa_id}", response_model=SpesaImmobile)
async def update_spesa(
    spesa_id: str,
    data: SpesaCreate,
    current_user: UserInDB = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """Aggiorna spesa."""
    if current_user.ruolo == UserRole.LETTURA:
        raise HTTPException(status_code=403, detail="Permessi insufficienti")
    
    existing = await db.spese.find_one({"id": spesa_id}, {"_id": 0})
    if not existing:
        raise HTTPException(status_code=404, detail="Spesa non trovata")
    
    update_dict = data.model_dump()
    update_dict["data"] = update_dict["data"].isoformat()
    
    await db.spese.update_one({"id": spesa_id}, {"$set": update_dict})
    await log_audit(db, "spese", spesa_id, "update", existing, update_dict, current_user.id)
    
    updated = await db.spese.find_one({"id": spesa_id}, {"_id": 0})
    return updated


@router.delete("/{spesa_id}")
async def delete_spesa(
    spesa_id: str,
    current_user: UserInDB = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """Elimina spesa."""
    if current_user.ruolo == UserRole.LETTURA:
        raise HTTPException(status_code=403, detail="Permessi insufficienti")
    
    existing = await db.spese.find_one({"id": spesa_id}, {"_id": 0})
    if not existing:
        raise HTTPException(status_code=404, detail="Spesa non trovata")
    
    await db.spese.delete_one({"id": spesa_id})
    await log_audit(db, "spese", spesa_id, "delete", existing, None, current_user.id)
    
    return {"message": "Spesa eliminata"}


@router.get("/categorie/lista")
async def get_categorie_spesa():
    """Ottieni lista categorie spesa."""
    return [{"value": c.value, "label": c.value.replace("_", " ").title()} for c in CategoriaSpesa]
