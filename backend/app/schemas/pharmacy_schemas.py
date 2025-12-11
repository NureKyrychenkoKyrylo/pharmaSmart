from pydantic import BaseModel
from datetime import date, datetime
from typing import List, Optional

# --- Місця зберігання (Холодильники) ---
class StorageLocationBase(BaseModel):
    name: str
    description: str | None = None
    is_refrigerated: bool = False

class StorageLocationCreate(StorageLocationBase):
    pharmacy_id: int

class StorageLocationResponse(StorageLocationBase):
    id: int
    pharmacy_id: int

    class Config:
        from_attributes = True

# --- Аптеки ---
class PharmacyBase(BaseModel):
    name: str
    address: str
    license_number: str
    license_expiry_date: Optional[date] = None
    phone: str | None = None

class PharmacyCreate(PharmacyBase):
    pass

class PharmacyResponse(PharmacyBase):
    id: int
    created_at: datetime
    # Можемо вкладати сюди список холодильників, якщо треба
    storage_locations: List[StorageLocationResponse] = []

    class Config:
        from_attributes = True