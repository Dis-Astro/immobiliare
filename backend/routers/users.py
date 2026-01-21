from fastapi import APIRouter, HTTPException, Depends, Query
from typing import List, Optional
from motor.motor_asyncio import AsyncIOMotorDatabase

from models.user import User, UserCreate, UserUpdate, UserInDB, UserRole
from utils.auth import get_password_hash
from routers.auth import get_current_user, get_db

router = APIRouter(prefix="/users", tags=["Utenti"])


@router.get("", response_model=List[User])
async def list_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    ruolo: Optional[UserRole] = None,
    attivo: Optional[bool] = None,
    current_user: UserInDB = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """Lista utenti (solo supervisore)."""
    if current_user.ruolo != UserRole.SUPERVISORE:
        raise HTTPException(status_code=403, detail="Permessi insufficienti")
    
    query = {}
    if ruolo:
        query["ruolo"] = ruolo
    if attivo is not None:
        query["attivo"] = attivo
    
    users = await db.users.find(query, {"_id": 0, "password_hash": 0}).skip(skip).limit(limit).to_list(limit)
    return users


@router.post("", response_model=User)
async def create_user(
    user_data: UserCreate,
    current_user: UserInDB = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """Crea nuovo utente (solo supervisore)."""
    if current_user.ruolo != UserRole.SUPERVISORE:
        raise HTTPException(status_code=403, detail="Permessi insufficienti")
    
    # Check if email exists
    existing = await db.users.find_one({"email": user_data.email})
    if existing:
        raise HTTPException(status_code=400, detail="Email già registrata")
    
    # Create user
    user = User(**user_data.model_dump(exclude={"password"}))
    user_dict = user.model_dump()
    user_dict["password_hash"] = get_password_hash(user_data.password)
    user_dict["must_change_password"] = True
    user_dict["created_at"] = user_dict["created_at"].isoformat()
    
    await db.users.insert_one(user_dict)
    
    return user


@router.get("/{user_id}", response_model=User)
async def get_user(
    user_id: str,
    current_user: UserInDB = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """Ottieni dettagli utente."""
    if current_user.ruolo != UserRole.SUPERVISORE and current_user.id != user_id:
        raise HTTPException(status_code=403, detail="Permessi insufficienti")
    
    user = await db.users.find_one({"id": user_id}, {"_id": 0, "password_hash": 0})
    if not user:
        raise HTTPException(status_code=404, detail="Utente non trovato")
    
    return user


@router.put("/{user_id}", response_model=User)
async def update_user(
    user_id: str,
    user_data: UserUpdate,
    current_user: UserInDB = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """Aggiorna utente (solo supervisore)."""
    if current_user.ruolo != UserRole.SUPERVISORE:
        raise HTTPException(status_code=403, detail="Permessi insufficienti")
    
    user = await db.users.find_one({"id": user_id})
    if not user:
        raise HTTPException(status_code=404, detail="Utente non trovato")
    
    update_dict = user_data.model_dump(exclude_unset=True)
    
    if "password" in update_dict and update_dict["password"]:
        update_dict["password_hash"] = get_password_hash(update_dict.pop("password"))
    elif "password" in update_dict:
        del update_dict["password"]
    
    if update_dict:
        await db.users.update_one({"id": user_id}, {"$set": update_dict})
    
    updated = await db.users.find_one({"id": user_id}, {"_id": 0, "password_hash": 0})
    return updated


@router.delete("/{user_id}")
async def delete_user(
    user_id: str,
    current_user: UserInDB = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """Disattiva utente (solo supervisore)."""
    if current_user.ruolo != UserRole.SUPERVISORE:
        raise HTTPException(status_code=403, detail="Permessi insufficienti")
    
    if current_user.id == user_id:
        raise HTTPException(status_code=400, detail="Non puoi disattivare te stesso")
    
    result = await db.users.update_one({"id": user_id}, {"$set": {"attivo": False}})
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Utente non trovato")
    
    return {"message": "Utente disattivato"}
