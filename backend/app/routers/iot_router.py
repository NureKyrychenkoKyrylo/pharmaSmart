from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

from app.db.database import get_db
from app.db.models import AuditLog, IoTDevice, SensorReading, Medicine, Batch, Alert, User, StorageLocation
from app.schemas.iot_schemas import ActiveAlertResponse, IncidentHistoryResponse, IoTDeviceCreate, IoTDeviceResponse, SensorReadingCreate, SensorReadingResponse
from app.api.deps import get_current_user, get_current_admin
from app.services.audit_service import log_action

router = APIRouter()

DEFAULT_REFRIGERATED_MIN_T = 2.0
DEFAULT_REFRIGERATED_MAX_T = 8.0
DEFAULT_MIN_HUMIDITY = 45.0
DEFAULT_MAX_HUMIDITY = 65.0
WARNING_TEMPERATURE_DELTA = 2.0
CRITICAL_TEMPERATURE_DELTA = 5.0
WARNING_HUMIDITY_DELTA = 5.0
CRITICAL_HUMIDITY_DELTA = 15.0


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


def calculate_deviation(value: float, min_value: float, max_value: float) -> float:
    if value < min_value:
        return min_value - value
    if value > max_value:
        return value - max_value
    return 0.0


def classify_alert_severity(
    temperature: float,
    humidity: float,
    min_t: float,
    max_t: float,
    min_h: float,
    max_h: float,
) -> str:
    temp_delta = calculate_deviation(temperature, min_t, max_t)
    humidity_delta = calculate_deviation(humidity, min_h, max_h)
    both_violated = temp_delta > 0 and humidity_delta > 0

    if (
        temp_delta >= CRITICAL_TEMPERATURE_DELTA
        or humidity_delta >= CRITICAL_HUMIDITY_DELTA
        or both_violated
    ):
        return "critical"

    if temp_delta >= WARNING_TEMPERATURE_DELTA or humidity_delta >= WARNING_HUMIDITY_DELTA:
        return "warning"

    return "warning"


def build_human_alert_message(
    subject: str,
    severity: str,
    temperature: float,
    humidity: float,
    min_t: float,
    max_t: float,
    min_h: float,
    max_h: float,
    is_location_level: bool = False,
) -> str:
    parts: List[str] = []

    if temperature > max_t or temperature < min_t:
        parts.append(
            f"температура {temperature:.1f}°C при нормі {min_t:.1f}-{max_t:.1f}°C"
        )

    if humidity > max_h or humidity < min_h:
        parts.append(
            f"вологість {humidity:.0f}% при нормі {min_h:.0f}-{max_h:.0f}%"
        )

    severity_label = "Критичне відхилення" if severity == "critical" else "Попередження"
    prefix = (
        f"{severity_label} в зоні зберігання «{subject}»."
        if is_location_level
        else f"{severity_label} для препарату «{subject}»."
    )
    details = " та ".join(parts) if parts else "Параметри вийшли за допустимі межі."
    return f"{prefix} Зафіксовано {details}."


def refresh_active_alert(
    db: Session,
    alert: Alert,
    severity: str,
    message: str,
    device: IoTDevice,
    subject: str,
    reading: SensorReadingCreate,
    scope: str,
):
    previous_message = alert.message
    alert.message = message
    alert.severity = severity
    alert.resolved_at = None
    alert.is_resolved = False

    if previous_message != message:
        log_action(
            db=db,
            user_id=None,
            action="ALERT_AUTO_UPDATED",
            details={
                "alert_id": alert.id,
                "device_id": device.id,
                "scope": scope,
                "subject": subject,
                "previous_message": previous_message,
                "current_message": message,
                "temperature": reading.temperature,
                "humidity": reading.humidity,
            },
        )


def resolve_device_context(
    db: Session,
    device_id: Optional[int] = None,
    alert_id: Optional[int] = None,
    device_serial_number: Optional[str] = None,
):
    device = None

    if device_id:
        device = db.query(IoTDevice).filter(IoTDevice.id == device_id).first()
    elif alert_id:
        alert = db.query(Alert).filter(Alert.id == alert_id).first()
        if alert:
            device = db.query(IoTDevice).filter(IoTDevice.id == alert.device_id).first()
    elif device_serial_number:
        device = db.query(IoTDevice).filter(IoTDevice.serial_number == device_serial_number).first()

    location = None
    pharmacy = None

    if device and device.storage_location_id:
        location = db.query(StorageLocation).filter(StorageLocation.id == device.storage_location_id).first()
        if location:
            pharmacy = location.pharmacy

    return device, location, pharmacy


def build_history_headline(action: str, subject: Optional[str], actor_name: Optional[str]) -> str:
    actor = actor_name or "Система"
    subject_text = f" «{subject}»" if subject else ""
    return {
        "ALERT_AUTO_CREATED": f"{actor} відкрила інцидент{subject_text}",
        "ALERT_AUTO_UPDATED": f"{actor} оновила інцидент{subject_text}",
        "ALERT_AUTO_RESOLVED": f"{actor} автоматично закрила інцидент{subject_text}",
        "ALERT_RESOLVED": f"{actor} закрив(ла) інцидент{subject_text}",
        "ALERT_ESCALATED": f"{actor} ескалював(ла) інцидент{subject_text}",
    }.get(action, f"{actor} зафіксував(ла) зміну інциденту{subject_text}")


def build_history_message(action: str, details: dict) -> str:
    if action == "ALERT_ESCALATED":
        return details.get("escalation_note") or "Інцидент позначено для негайної уваги відповідального працівника."
    if action == "ALERT_AUTO_UPDATED":
        return details.get("current_message") or details.get("message") or "Параметри інциденту були оновлені."
    return details.get("message") or details.get("reason") or "Подія зафіксована в журналі."


def extract_subject_from_message(message: str) -> Optional[str]:
    if "«" in message and "»" in message:
        return message.split("«", 1)[1].split("»", 1)[0].strip()
    return None

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
                severity = classify_alert_severity(
                    temperature=reading.temperature,
                    humidity=reading.humidity,
                    min_t=min_t,
                    max_t=max_t,
                    min_h=min_h,
                    max_h=max_h,
                )
                msg_text = build_human_alert_message(
                    subject=medicine.name,
                    severity=severity,
                    temperature=reading.temperature,
                    humidity=reading.humidity,
                    min_t=min_t,
                    max_t=max_t,
                    min_h=min_h,
                    max_h=max_h,
                )
                
                if existing_med_alert:
                    refresh_active_alert(
                        db=db,
                        alert=existing_med_alert,
                        severity=severity,
                        message=msg_text,
                        device=device,
                        subject=medicine.name,
                        reading=reading,
                        scope="medicine",
                    )
                    print(f"[AUTO] Alert Updated: {msg_text}")
                else:
                    new_alert = Alert(
                        device_id=device.id,
                        severity=severity,
                        message=msg_text,
                        is_resolved=False
                    )
                    db.add(new_alert)
                    log_action(
                        db,
                        user_id=None,
                        action="ALERT_AUTO_CREATED",
                        details={
                            "device_id": device.id,
                            "scope": "medicine",
                            "subject": medicine.name,
                            "message": msg_text,
                            "temperature": reading.temperature,
                            "humidity": reading.humidity,
                        },
                    )
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

            generic_message = build_human_alert_message(
                subject=location.name,
                severity=classify_alert_severity(
                    temperature=reading.temperature,
                    humidity=reading.humidity,
                    min_t=DEFAULT_REFRIGERATED_MIN_T,
                    max_t=DEFAULT_REFRIGERATED_MAX_T,
                    min_h=DEFAULT_MIN_HUMIDITY,
                    max_h=DEFAULT_MAX_HUMIDITY,
                ),
                temperature=reading.temperature,
                humidity=reading.humidity,
                min_t=DEFAULT_REFRIGERATED_MIN_T,
                max_t=DEFAULT_REFRIGERATED_MAX_T,
                min_h=DEFAULT_MIN_HUMIDITY,
                max_h=DEFAULT_MAX_HUMIDITY,
                is_location_level=True,
            ) if default_violations else ""
            existing_generic_alert = next(
                (alert for alert in active_alerts if location.name in alert.message),
                None
            )

            if default_violations:
                severity = classify_alert_severity(
                    temperature=reading.temperature,
                    humidity=reading.humidity,
                    min_t=DEFAULT_REFRIGERATED_MIN_T,
                    max_t=DEFAULT_REFRIGERATED_MAX_T,
                    min_h=DEFAULT_MIN_HUMIDITY,
                    max_h=DEFAULT_MAX_HUMIDITY,
                )
                if existing_generic_alert:
                    refresh_active_alert(
                        db=db,
                        alert=existing_generic_alert,
                        severity=severity,
                        message=generic_message,
                        device=device,
                        subject=location.name,
                        reading=reading,
                        scope="location",
                    )
                    print(f"[AUTO] Fallback Alert Updated: {generic_message}")
                else:
                    db.add(Alert(
                        device_id=device.id,
                        severity=severity,
                        message=generic_message,
                        is_resolved=False,
                    ))
                    log_action(
                        db,
                        user_id=None,
                        action="ALERT_AUTO_CREATED",
                        details={
                            "device_id": device.id,
                            "scope": "location",
                            "subject": location.name,
                            "message": generic_message,
                            "temperature": reading.temperature,
                            "humidity": reading.humidity,
                        },
                    )
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


@router.get("/incidents/history", response_model=List[IncidentHistoryResponse], summary="Журнал інцидентів")
def get_incident_history(
    pharmacy_id: Optional[int] = None,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    log_actions = [
        "ALERT_AUTO_CREATED",
        "ALERT_AUTO_UPDATED",
        "ALERT_AUTO_RESOLVED",
        "ALERT_RESOLVED",
        "ALERT_ESCALATED",
    ]
    logs = db.query(AuditLog) \
        .filter(AuditLog.action.in_(log_actions)) \
        .order_by(AuditLog.created_at.desc()) \
        .limit(max(limit, 1)) \
        .all()

    result: List[IncidentHistoryResponse] = []
    for log in logs:
        details = log.details or {}
        device, location, pharmacy = resolve_device_context(
            db=db,
            device_id=details.get("device_id"),
            alert_id=details.get("alert_id"),
            device_serial_number=details.get("device_sn"),
        )

        if current_user.role != "admin":
            if not current_user.pharmacy_id or not pharmacy or pharmacy.id != current_user.pharmacy_id:
                continue
        elif pharmacy_id and (not pharmacy or pharmacy.id != pharmacy_id):
            continue

        actor_name = log.user.full_name if log.user else "Система"
        subject = details.get("subject")

        result.append(
            IncidentHistoryResponse(
                id=log.id,
                action=log.action,
                headline=build_history_headline(log.action, subject, actor_name),
                message=build_history_message(log.action, details),
                created_at=log.created_at,
                pharmacy_name=details.get("pharmacy_name") or (pharmacy.name if pharmacy else None),
                storage_location_name=details.get("storage_location_name") or (location.name if location else None),
                device_serial_number=details.get("device_sn") or (device.serial_number if device else None),
                actor_name=actor_name,
                alert_id=details.get("alert_id"),
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
            "device_id": device.id,
            "device_sn": device.serial_number,
            "message": alert.message,
            "subject": extract_subject_from_message(alert.message),
            "pharmacy_name": location.pharmacy.name if location and location.pharmacy else None,
            "storage_location_name": location.name if location else None,
        }
    )
    
    db.commit()
    return {"status": "resolved"}


@router.put("/alerts/{alert_id}/escalate", summary="Ескалувати інцидент")
def escalate_alert(
    alert_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    device = db.query(IoTDevice).filter(IoTDevice.id == alert.device_id).first()
    location = db.query(StorageLocation).filter(StorageLocation.id == device.storage_location_id).first() if device and device.storage_location_id else None
    pharmacy = location.pharmacy if location else None

    if current_user.role != "admin":
        if not current_user.pharmacy_id or not pharmacy or pharmacy.id != current_user.pharmacy_id:
            raise HTTPException(status_code=403, detail="Not your alert")

    log_action(
        db,
        user_id=current_user.id,
        action="ALERT_ESCALATED",
        details={
            "alert_id": alert.id,
            "device_id": device.id if device else None,
            "device_sn": device.serial_number if device else None,
            "message": alert.message,
            "subject": extract_subject_from_message(alert.message),
            "pharmacy_name": pharmacy.name if pharmacy else None,
            "storage_location_name": location.name if location else None,
            "escalation_note": "Інцидент ескальовано: потрібна перевірка обладнання, оцінка ризику для партій та контроль повторного вимірювання.",
        },
    )
    db.commit()
    return {"status": "escalated"}
