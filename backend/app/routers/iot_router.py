from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

from app.db.database import get_db
from app.db.models import IoTDevice, SensorReading, Medicine, Batch, Alert, User, StorageLocation
from app.schemas.iot_schemas import ActiveAlertResponse, IoTDeviceCreate, IoTDeviceResponse, SensorReadingCreate, SensorReadingResponse
from app.api.deps import get_current_user, get_current_admin
from app.services.audit_service import log_action

router = APIRouter()

DEFAULT_REFRIGERATED_MIN_T = 2.0
DEFAULT_REFRIGERATED_MAX_T = 8.0
DEFAULT_MIN_HUMIDITY = 45.0
DEFAULT_MAX_HUMIDITY = 65.0


def build_violation_reasons(
    temperature: float,
    humidity: float,
    min_t: float,
    max_t: float,
    min_h: float,
    max_h: float,
) -> List[str]:
    violation_reasons: List[str] = []

    if temperature > max_t or temperature < min_t:
        violation_reasons.append(f"Temp {temperature}°C (Limit: {min_t}-{max_t})")

    if humidity > max_h or humidity < min_h:
        violation_reasons.append(f"Humidity {humidity}% (Limit: {min_h}-{max_h})")

    return violation_reasons


def refresh_active_alert(alert: Alert, message: str):
    alert.message = message
    alert.severity = "critical"
    # We reuse created_at as the latest trigger timestamp because the schema
    # does not yet have a dedicated updated_at/triggered_at field.
    alert.created_at = datetime.utcnow()
    alert.resolved_at = None
    alert.is_resolved = False

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
    description="Аналізує Температуру ТА Вологість."
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
    device.last_seen = datetime.utcnow()
    
    if device.storage_location_id:
        location = db.query(StorageLocation).filter(StorageLocation.id == device.storage_location_id).first()
        active_alerts = db.query(Alert).filter(
            Alert.device_id == device.id, 
            Alert.is_resolved == False
        ).all()

        batches_here = db.query(Batch).filter(Batch.storage_location_id == device.storage_location_id).all()
        unique_medicines = {batch.medicine for batch in batches_here}

        for medicine in unique_medicines:
            min_t, max_t = medicine.min_temperature, medicine.max_temperature
            min_h, max_h = medicine.min_humidity, medicine.max_humidity
            
            existing_med_alert = next((a for a in active_alerts if medicine.name in a.message), None)
            violation_reasons = build_violation_reasons(
                temperature=reading.temperature,
                humidity=reading.humidity,
                min_t=min_t,
                max_t=max_t,
                min_h=min_h,
                max_h=max_h,
            )

            if violation_reasons:
                msg_text = f"Critical: {medicine.name} -> " + ", ".join(violation_reasons)
                
                if existing_med_alert:
                    refresh_active_alert(existing_med_alert, msg_text)
                    print(f"[AUTO] Alert Updated: {msg_text}")
                else:
                    new_alert = Alert(
                        device_id=device.id,
                        severity="critical",
                        message=msg_text,
                        is_resolved=False
                    )
                    db.add(new_alert)
                    print(f"[AUTO] Alert Created: {msg_text}")
            
            else:
                if existing_med_alert:
                    existing_med_alert.is_resolved = True
                    existing_med_alert.resolved_at = datetime.utcnow()
                    log_action(db, user_id=None, action="ALERT_AUTO_RESOLVED", 
                               details={"medicine": medicine.name, "reason": "Conditions normalized"})
                    print(f"[AUTO] Alert Resolved for {medicine.name}")

        if not unique_medicines and location:
            default_violations = build_violation_reasons(
                temperature=reading.temperature,
                humidity=reading.humidity,
                min_t=DEFAULT_REFRIGERATED_MIN_T,
                max_t=DEFAULT_REFRIGERATED_MAX_T,
                min_h=DEFAULT_MIN_HUMIDITY,
                max_h=DEFAULT_MAX_HUMIDITY,
            )

            generic_message = f"Critical: {location.name} -> " + ", ".join(default_violations) if default_violations else ""
            existing_generic_alert = next(
                (alert for alert in active_alerts if alert.message.startswith(f"Critical: {location.name} ->")),
                None
            )

            if default_violations:
                if existing_generic_alert:
                    refresh_active_alert(existing_generic_alert, generic_message)
                    print(f"[AUTO] Fallback Alert Updated: {generic_message}")
                else:
                    db.add(Alert(
                        device_id=device.id,
                        severity="critical",
                        message=generic_message,
                        is_resolved=False,
                    ))
                    print(f"[AUTO] Fallback Alert Created: {generic_message}")
            elif not default_violations and existing_generic_alert:
                existing_generic_alert.is_resolved = True
                existing_generic_alert.resolved_at = datetime.utcnow()
                log_action(
                    db,
                    user_id=None,
                    action="ALERT_AUTO_RESOLVED",
                    details={"location": location.name, "reason": "Conditions normalized"},
                )
                print(f"[AUTO] Fallback Alert Resolved for {location.name}")

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
@router.get("/alerts", response_model=List[ActiveAlertResponse], summary="Список активних тривог")
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
        
    alerts = query.order_by(Alert.created_at.desc()).all()

    result: List[ActiveAlertResponse] = []
    for alert in alerts:
        device = db.query(IoTDevice).filter(IoTDevice.id == alert.device_id).first()
        location = None
        pharmacy = None
        latest_reading = None

        if device and device.storage_location_id:
            location = db.query(StorageLocation).filter(StorageLocation.id == device.storage_location_id).first()
            if location:
                pharmacy = db.query(StorageLocation).filter(StorageLocation.id == location.id).first()
                pharmacy = location.pharmacy

            latest_reading = db.query(SensorReading)\
                .filter(SensorReading.device_id == device.id)\
                .order_by(SensorReading.recorded_at.desc())\
                .first()

        result.append(
            ActiveAlertResponse(
                id=alert.id,
                device_id=alert.device_id,
                severity=alert.severity,
                message=alert.message,
                is_resolved=alert.is_resolved,
                created_at=alert.created_at,
                pharmacy_name=pharmacy.name if pharmacy else None,
                storage_location_name=location.name if location else None,
                device_serial_number=device.serial_number if device else None,
                latest_temperature=latest_reading.temperature if latest_reading else None,
                latest_humidity=latest_reading.humidity if latest_reading else None,
            )
        )

    return result

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
