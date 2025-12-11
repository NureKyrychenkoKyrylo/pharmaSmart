from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import date, timedelta

from app.db.database import get_db
from app.db.models import Medicine, Batch, StorageLocation, User, Pharmacy
from app.schemas.inventory_schemas import MedicineCreate, MedicineResponse, BatchCreate, BatchResponse, BatchDispose
from app.api.deps import get_current_user, get_current_admin
from app.services.audit_service import log_action

router = APIRouter()

# НОМЕНКЛАТУРА ЛІКІВ (Глобальний довідник)
@router.post(
    "/medicines",
    response_model=MedicineResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Додати ліки в довідник",
    description="Доступно тільки Адміністратору. Створює картку товару.",
    responses={
        403: {"description": "Тільки адмін може додавати нові ліки"}
    }
)
def create_medicine(
    medicine: MedicineCreate, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin) # Тільки Адмін
):
    db_medicine = Medicine(**medicine.model_dump())
    db.add(db_medicine)
    db.commit()
    db.refresh(db_medicine)
    return db_medicine

@router.get(
    "/medicines",
    response_model=List[MedicineResponse],
    summary="Отримати список ліків",
    description="Доступно всім авторизованим користувачам."
)
def get_medicines(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return db.query(Medicine).all()

@router.delete(
    "/medicines/{medicine_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Видалити ліки з довідника",
    responses={
        403: {"description": "Недостатньо прав"},
        404: {"description": "Ліки не знайдено"}
    }
)
def delete_medicine(
    medicine_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin) # Тільки Адмін
):
    medicine = db.query(Medicine).filter(Medicine.id == medicine_id).first()
    if not medicine:
        raise HTTPException(status_code=404, detail="Medicine not found")
    
    # Тут може виникнути помилка IntegrityError, якщо є партії цих ліків.
    # Але це правильно - не можна видаляти ліки, які є на складі.
    db.delete(medicine)
    db.commit()
    return None


# СКЛАДСЬКИЙ ОБЛІК (Batches)
@router.post(
    "/batches",
    response_model=BatchResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Прийом товару (Створення партії)",
    description="Менеджер може додавати товар ТІЛЬКИ у свої холодильники.",
    responses={
        403: {"description": "Спроба додати товар у чужу аптеку"},
        404: {"description": "Місце зберігання або ліки не знайдено"}
    }
)
def add_batch(
    batch: BatchCreate, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    location = db.query(StorageLocation).filter(StorageLocation.id == batch.storage_location_id).first()
    if not location:
        raise HTTPException(status_code=404, detail="Storage location not found")

    if current_user.role != "admin":
        if location.pharmacy_id != current_user.pharmacy_id:
            raise HTTPException(
                status_code=403, 
                detail="You can only add batches to your own pharmacy storage locations"
            )

    medicine = db.query(Medicine).filter(Medicine.id == batch.medicine_id).first()
    if not medicine:
        raise HTTPException(status_code=404, detail="Medicine ID not found")

    db_batch = Batch(**batch.model_dump())
    db.add(db_batch)
    db.commit()
    db.refresh(db_batch)
    return db_batch

@router.get(
    "/batches",
    response_model=List[BatchResponse],
    summary="Перегляд залишків на складі",
    description="Адмін бачить все (може фільтрувати). Менеджер - тільки свою аптеку."
)
def read_batches(
    pharmacy_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = db.query(Batch).join(StorageLocation)

    if current_user.role == "admin":
        if pharmacy_id:
            query = query.filter(StorageLocation.pharmacy_id == pharmacy_id)
    else:
        if not current_user.pharmacy_id:
            return []
        query = query.filter(StorageLocation.pharmacy_id == current_user.pharmacy_id)

    return query.all()

@router.delete(
    "/batches/{batch_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Списання/Видалення партії",
    responses={
        403: {"description": "Спроба видалити чужу партію"},
        404: {"description": "Партія не знайдена"}
    }
)
def delete_batch(
    batch_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    batch = db.query(Batch).filter(Batch.id == batch_id).first()
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")

    if current_user.role != "admin":
        location = db.query(StorageLocation).filter(StorageLocation.id == batch.storage_location_id).first()
        
        if not location or location.pharmacy_id != current_user.pharmacy_id:
            raise HTTPException(status_code=403, detail="You can only delete batches in your pharmacy")

    db.delete(batch)
    db.commit()
    return None

@router.get("/expired", response_model=List[BatchResponse])
def get_expired_batches(
    days_to_expire: int = 0,
    pharmacy_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Пошук ліків, термін дії яких спливає.
    - days_to_expire=0: Покаже тільки те, що ВЖЕ прострочено (сьогодні або раніше).
    - days_to_expire=30: Покаже те, що прострочено + те, що зіпсується за 30 днів.
    """
    today = date.today()
    target_date = today + timedelta(days=days_to_expire)
    
    # Шукаємо партії де дата закінчення <= (сьогодні + N днів)
    # І при цьому товару має бути > 0
    query = db.query(Batch).join(StorageLocation).filter(
        Batch.expiration_date <= target_date,
        Batch.current_quantity > 0
    )

    if current_user.role == "admin":
        if pharmacy_id:
            query = query.filter(StorageLocation.pharmacy_id == pharmacy_id)
    else:
        if not current_user.pharmacy_id:
            return []
        query = query.filter(StorageLocation.pharmacy_id == current_user.pharmacy_id)

    return query.order_by(Batch.expiration_date.asc()).all()

# СПИСАННЯ ТОВАРУ (Disposal)
@router.post("/dispose", status_code=status.HTTP_200_OK)
def dispose_batch(
    disposal_data: BatchDispose,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Списання товару (зіпсувався, розбився, прострочений).
    Тільки Менеджер (своя аптека) або Адмін.
    """
    batch = db.query(Batch).filter(Batch.id == disposal_data.batch_id).first()
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")

    location = db.query(StorageLocation).filter(StorageLocation.id == batch.storage_location_id).first()
    
    if current_user.role != "admin":
        if location.pharmacy_id != current_user.pharmacy_id:
             raise HTTPException(status_code=403, detail="You can only dispose items in your pharmacy")

    if batch.current_quantity < disposal_data.quantity:
        raise HTTPException(status_code=400, detail="Not enough items to dispose")

    batch.current_quantity -= disposal_data.quantity

    # Запис в Аудит 
    log_action(
        db,
        user_id=current_user.id,
        action="BATCH_DISPOSAL",
        details={
            "batch_number": batch.batch_number,
            "medicine_id": batch.medicine_id,
            "quantity_removed": disposal_data.quantity,
            "reason": disposal_data.reason,
            "pharmacy_id": location.pharmacy_id
        }
    )

    db.commit()
    return {"message": "Batch disposed successfully", "remaining_quantity": batch.current_quantity}