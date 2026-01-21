from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorDatabase

from models.user import User, UserCreate, UserInDB, UserRole
from utils.auth import (
    verify_password, 
    get_password_hash, 
    create_access_token, 
    create_refresh_token,
    decode_token
)

router = APIRouter(prefix="/auth", tags=["Autenticazione"])

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: dict


class TokenRefresh(BaseModel):
    refresh_token: str


class PasswordChange(BaseModel):
    current_password: str
    new_password: str


# Dependency to get database
async def get_db():
    from server import db
    return db


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncIOMotorDatabase = Depends(get_db)
) -> UserInDB:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Credenziali non valide",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    payload = decode_token(token)
    if payload is None:
        raise credentials_exception
    
    if payload.get("type") != "access":
        raise credentials_exception
    
    user_id: str = payload.get("sub")
    if user_id is None:
        raise credentials_exception
    
    user_doc = await db.users.find_one({"id": user_id}, {"_id": 0})
    if user_doc is None:
        raise credentials_exception
    
    if not user_doc.get("attivo", True):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Utente disattivato"
        )
    
    return UserInDB(**user_doc)


async def require_role(*roles: UserRole):
    async def role_checker(current_user: UserInDB = Depends(get_current_user)):
        if current_user.ruolo not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Permessi insufficienti"
            )
        return current_user
    return role_checker


def check_role(user: UserInDB, *roles: UserRole) -> bool:
    return user.ruolo in roles


@router.post("/login", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """Login utente con email e password."""
    user_doc = await db.users.find_one({"email": form_data.username}, {"_id": 0})
    
    if not user_doc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email o password non corretti"
        )
    
    user = UserInDB(**user_doc)
    
    if not verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email o password non corretti"
        )
    
    if not user.attivo:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Utente disattivato"
        )
    
    # Update last login
    await db.users.update_one(
        {"id": user.id},
        {"$set": {"last_login": datetime.now(timezone.utc).isoformat()}}
    )
    
    access_token = create_access_token(data={"sub": user.id, "ruolo": user.ruolo})
    refresh_token = create_refresh_token(data={"sub": user.id})
    
    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        user={
            "id": user.id,
            "email": user.email,
            "nome": user.nome,
            "ruolo": user.ruolo,
            "must_change_password": user.must_change_password
        }
    )


@router.post("/refresh", response_model=Token)
async def refresh_token(
    token_data: TokenRefresh,
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """Rinnova access token usando refresh token."""
    payload = decode_token(token_data.refresh_token)
    
    if payload is None or payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token non valido"
        )
    
    user_id = payload.get("sub")
    user_doc = await db.users.find_one({"id": user_id}, {"_id": 0})
    
    if not user_doc or not user_doc.get("attivo", True):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Utente non trovato o disattivato"
        )
    
    user = UserInDB(**user_doc)
    
    access_token = create_access_token(data={"sub": user.id, "ruolo": user.ruolo})
    new_refresh_token = create_refresh_token(data={"sub": user.id})
    
    return Token(
        access_token=access_token,
        refresh_token=new_refresh_token,
        user={
            "id": user.id,
            "email": user.email,
            "nome": user.nome,
            "ruolo": user.ruolo,
            "must_change_password": user.must_change_password
        }
    )


@router.get("/me")
async def get_me(current_user: UserInDB = Depends(get_current_user)):
    """Ottieni informazioni utente corrente."""
    return {
        "id": current_user.id,
        "email": current_user.email,
        "nome": current_user.nome,
        "ruolo": current_user.ruolo,
        "attivo": current_user.attivo,
        "must_change_password": current_user.must_change_password,
        "last_login": current_user.last_login
    }


@router.post("/change-password")
async def change_password(
    password_data: PasswordChange,
    current_user: UserInDB = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """Cambia password utente."""
    if not verify_password(password_data.current_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password attuale non corretta"
        )
    
    new_hash = get_password_hash(password_data.new_password)
    
    await db.users.update_one(
        {"id": current_user.id},
        {"$set": {
            "password_hash": new_hash,
            "must_change_password": False
        }}
    )
    
    return {"message": "Password aggiornata con successo"}
