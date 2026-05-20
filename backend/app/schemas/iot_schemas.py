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


class ActiveAlertResponse(BaseModel):
    id: int
    device_id: int
    severity: str
    message: str
    is_resolved: bool
    created_at: datetime
    pharmacy_name: Optional[str] = None
    storage_location_name: Optional[str] = None
    device_serial_number: Optional[str] = None
    latest_temperature: Optional[float] = None
    latest_humidity: Optional[float] = None

    class Config:
        from_attributes = True


class IncidentHistoryResponse(BaseModel):
    id: int
    action: str
    headline: str
    message: str
    created_at: datetime
    pharmacy_name: Optional[str] = None
    storage_location_name: Optional[str] = None
    device_serial_number: Optional[str] = None
    actor_name: Optional[str] = None
    alert_id: Optional[int] = None

    class Config:
        from_attributes = True
