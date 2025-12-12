from pydantic import BaseModel
from datetime import date, datetime

# --- Ліки (Номенклатура) ---
    
class MedicineBase(BaseModel):
    name: str
    manufacturer: str | None = None
    description: str | None = None
    
    min_temperature: float
    max_temperature: float
    
    min_humidity: float = 0.0
    max_humidity: float = 65.0
    
    is_prescription: bool = False
    requires_smart_lock: bool = False

  

class MedicineCreate(MedicineBase):
    pass

class MedicineResponse(MedicineBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True

# --- Партії (Склад) ---
class BatchBase(BaseModel):
    batch_number: str
    initial_quantity: int
    current_quantity: int
    expiration_date: date

class BatchCreate(BatchBase):
    medicine_id: int
    storage_location_id: int

class BatchResponse(BatchBase):
    id: int
    medicine_id: int
    storage_location_id: int
    arrival_date: datetime

    class Config:
        from_attributes = True

class BatchDispose(BaseModel):
    batch_id: int
    quantity: int
    reason: str # Наприклад: "Expired", "Damaged", "Lost"