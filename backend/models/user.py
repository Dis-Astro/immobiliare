from pydantic import BaseModel, Field, EmailStr, ConfigDict
from typing import Optional
from datetime import datetime, timezone
from enum import Enum
import uuid


class UserRole(str, Enum):
    SUPERVISORE = "supervisore"
    GESTORE = "gestore"
    LETTURA = "lettura"


class UserBase(BaseModel):
    email: EmailStr
    nome: str
    ruolo: UserRole = UserRole.GESTORE
    attivo: bool = True


class UserCreate(UserBase):
    password: str


class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    nome: Optional[str] = None
    ruolo: Optional[UserRole] = None
    attivo: Optional[bool] = None
    password: Optional[str] = None
    must_change_password: Optional[bool] = None


class User(UserBase):
    model_config = ConfigDict(extra="ignore")
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_login: Optional[datetime] = None
    must_change_password: bool = False


class UserInDB(User):
    password_hash: str
