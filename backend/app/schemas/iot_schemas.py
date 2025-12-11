from pydantic import BaseModel
from datetime import datetime
from typing import Optional

# --- Показники (Телеметрія) ---
class SensorReadingCreate(BaseModel):
    # Пристрій не знає свого ID в базі, він знає тільки серійний номер,
    # тому ми приймаємо чисті дані
    temperature: float
    humidity: float
    battery_level: int

class SensorReadingResponse(SensorReadingCreate):
    id: int
    device_id: int
    recorded_at: datetime

    class Config:
        from_attributes = True

# --- Пристрої ---
class IoTDeviceBase(BaseModel):
    serial_number: str
    device_type: str # 'sensor', 'smart_lock'
    status: str = 'active'

class IoTDeviceCreate(IoTDeviceBase):
    storage_location_id: int

class IoTDeviceResponse(IoTDeviceBase):
    id: int
    storage_location_id: Optional[int] = None
    last_seen: Optional[datetime] = None

    class Config:
        from_attributes = True

# --- Алерти (Тривоги) ---
class AlertResponse(BaseModel):
    id: int
    device_id: int
    severity: str
    message: str
    is_resolved: bool
    created_at: datetime

    class Config:
        from_attributes = True