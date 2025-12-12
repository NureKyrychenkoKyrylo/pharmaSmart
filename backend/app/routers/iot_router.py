from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

from app.db.database import get_db
from app.db.models import IoTDevice, SensorReading, Medicine, Batch, Alert, User, StorageLocation
from app.schemas.iot_schemas import IoTDeviceCreate, IoTDeviceResponse, SensorReadingCreate, SensorReadingResponse
from app.api.deps import get_current_user, get_current_admin
from app.services.audit_service import log_action

router = APIRouter()

# РЕЄСТРАЦІЯ ПРИСТРОЮ (Адміністративна панель)
@router.post(
    "/devices",
    response_model=IoTDeviceResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Реєстрація нового IoT датчика",
    description="Менеджер може додати датчик ТІЛЬКИ у свої холодильники.",
    responses={
        403: {"description": "Спроба додати датчик у чужу аптеку"},
        404: {"description": "Місце зберігання не знайдено"}
    }
)
def register_device(
    device: IoTDeviceCreate, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    location = db.query(StorageLocation).filter(StorageLocation.id == device.storage_location_id).first()
    if not location:
        raise HTTPException(status_code=404, detail="Storage location not found")

    if current_user.role != "admin":
        if current_user.role == "pharmacist":
             raise HTTPException(status_code=403, detail="Pharmacists cannot register devices")
        
        if location.pharmacy_id != current_user.pharmacy_id:
            raise HTTPException(
                status_code=403, 
                detail="You can only register devices in your pharmacy"
            )

    # Перевірка на дублікат серійного номеру
    if db.query(IoTDevice).filter(IoTDevice.serial_number == device.serial_number).first():
        raise HTTPException(status_code=400, detail="Device with this Serial Number already exists")

    db_device = IoTDevice(
        serial_number=device.serial_number,
        device_type=device.device_type,
        status=device.status,
        storage_location_id=device.storage_location_id
    )
    db.add(db_device)
    db.commit()
    db.refresh(db_device)
    return db_device



@router.post(
    "/devices/{serial_number}/readings", 
    response_model=SensorReadingResponse,
    summary="Прийом телеметрії",
    description="Автоматично створює тривоги при порушенні і ЗАКРИВАЄ їх при нормалізації."
)
def receive_metrics(
    serial_number: str, 
    reading: SensorReadingCreate, 
    db: Session = Depends(get_db)
):
    device = db.query(IoTDevice).filter(IoTDevice.serial_number == serial_number).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    db_reading = SensorReading(
        device_id=device.id,
        temperature=reading.temperature,
        humidity=reading.humidity,
        battery_level=reading.battery_level
    )
    db.add(db_reading)
    
    if device.storage_location_id:
        existing_alert = db.query(Alert).filter(
            Alert.device_id == device.id, 
            Alert.is_resolved == False
        ).first()

        batches_here = db.query(Batch).filter(Batch.storage_location_id == device.storage_location_id).all()
        
        is_critical_state = False
        violation_msg = ""

        for batch in batches_here:
            min_t = batch.medicine.min_temperature
            max_t = batch.medicine.max_temperature
            
            if reading.temperature > max_t or reading.temperature < min_t:
                is_critical_state = True
                violation_msg = f"Critical: {batch.medicine.name} needs {min_t}-{max_t}°C, but current is {reading.temperature}°C"
                break

        # --- ЛОГІКА РІШЕНЬ ---
        
        if is_critical_state:
            if not existing_alert:
                new_alert = Alert(
                    device_id=device.id,
                    severity="critical",
                    message=violation_msg
                )
                db.add(new_alert)
                print(f"[AUTO] Alert Created for {device.serial_number}")
        
        else:
            if existing_alert:
                existing_alert.is_resolved = True
                existing_alert.resolved_at = datetime.utcnow()
                
                log_action(
                    db,
                    user_id=None, 
                    action="ALERT_AUTO_RESOLVED",
                    details={
                        "alert_id": existing_alert.id,
                        "reason": f"Temperature normalized to {reading.temperature}°C",
                        "device": device.serial_number
                    }
                )
                print(f"[AUTO] Alert Resolved for {device.serial_number}")

    db.commit()
    db.refresh(db_reading)
    return db_reading


# ВИДАЛЕННЯ ПРИСТРОЮ
@router.delete(
    "/devices/{device_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Видалення/Списання датчика",
    responses={
        403: {"description": "Спроба видалити чужий пристрій"}
    }
)
def delete_device(
    device_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    device = db.query(IoTDevice).filter(IoTDevice.id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    # Перевірка прав
    if current_user.role != "admin":
        # Перевіряємо, чи пристрій належить аптеці менеджера
        if device.storage_location_id:
            location = db.query(StorageLocation).filter(StorageLocation.id == device.storage_location_id).first()
            if not location or location.pharmacy_id != current_user.pharmacy_id:
                raise HTTPException(status_code=403, detail="Not your device")
        else:
             # Якщо пристрій ніде не встановлений, видаляти може тільки адмін
             raise HTTPException(status_code=403, detail="Only admin can delete unassigned devices")

    db.delete(device)
    db.commit()
    return None


# ПЕРЕГЛЯД ПРИСТРОЇВ
@router.get(
    "/devices",
    response_model=List[IoTDeviceResponse],
    summary="Список датчиків",
    description="Менеджер бачить тільки свої. Адмін - усі."
)
def read_devices(
    pharmacy_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = db.query(IoTDevice)

    if current_user.role == "admin":
        if pharmacy_id:
            query = query.join(StorageLocation).filter(StorageLocation.pharmacy_id == pharmacy_id)
    else:
        if not current_user.pharmacy_id:
            return []
        query = query.join(StorageLocation).filter(StorageLocation.pharmacy_id == current_user.pharmacy_id)

    return query.all()

# ОТРИМАННЯ АКТИВНИХ ТРИВОГ
@router.get("/alerts", summary="Список активних тривог")
def get_active_alerts(
    pharmacy_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Join таблиць: Alert -> Device -> Location
    query = db.query(Alert).join(IoTDevice).join(StorageLocation).filter(Alert.is_resolved == False)

    if current_user.role == "admin":
        if pharmacy_id:
            query = query.filter(StorageLocation.pharmacy_id == pharmacy_id)
    else:
        if not current_user.pharmacy_id:
            return []
        query = query.filter(StorageLocation.pharmacy_id == current_user.pharmacy_id)
        
    return query.all()

# ВИРІШЕННЯ ТРИВОГИ (Resolve)
@router.put("/alerts/{alert_id}/resolve", summary="Закрити інцидент")
def resolve_alert(
    alert_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    
    device = db.query(IoTDevice).filter(IoTDevice.id == alert.device_id).first()
    location = db.query(StorageLocation).filter(StorageLocation.id == device.storage_location_id).first()
    
    if current_user.role != "admin":
        if location.pharmacy_id != current_user.pharmacy_id:
            raise HTTPException(status_code=403, detail="Not your alert")

    # Логіка закриття
    alert.is_resolved = True
    alert.resolved_at = datetime.utcnow()
    
    # Аудит
    log_action(
        db,
        user_id=current_user.id,
        action="ALERT_RESOLVED",
        details={
            "alert_id": alert.id,
            "device_sn": device.serial_number,
            "message": alert.message
        }
    )
    
    db.commit()
    return {"status": "resolved"}