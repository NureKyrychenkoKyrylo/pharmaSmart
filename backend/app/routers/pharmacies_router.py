from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional

from app.db.database import get_db
from app.db.models import Pharmacy, StorageLocation, User
from app.schemas.pharmacy_schemas import PharmacyCreate, PharmacyResponse, StorageLocationCreate, StorageLocationResponse
from app.api.deps import get_current_user, get_current_admin

router = APIRouter()

# УПРАВЛІННЯ АПТЕКАМИ

@router.post(
    "/", 
    response_model=PharmacyResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Створити нову аптеку",
    description="Доступно тільки Адміністратору.",
    responses={
        403: {"description": "Недостатньо прав"}
    }
)
def create_pharmacy(
    pharmacy: PharmacyCreate, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin) 
):
    # Перевірка на унікальність ліцензії
    if db.query(Pharmacy).filter(Pharmacy.license_number == pharmacy.license_number).first():
        raise HTTPException(status_code=400, detail="Pharmacy with this license already exists")

    db_pharmacy = Pharmacy(
        name=pharmacy.name,
        address=pharmacy.address,
        license_number=pharmacy.license_number,
        license_expiry_date=pharmacy.license_expiry_date,
        phone=pharmacy.phone
    )
    db.add(db_pharmacy)
    db.commit()
    db.refresh(db_pharmacy)
    return db_pharmacy


@router.get(
    "/", 
    response_model=List[PharmacyResponse],
    summary="Отримати список аптек",
    description="Адмін бачить усі. Менеджер і Фармацевт - тільки свою."
)
def read_pharmacies(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = db.query(Pharmacy)

    if current_user.role == "admin":
        # Адмін бачить все
        return query.all()
    else:
        # Інші бачать тільки ту аптеку, до якої прив'язані
        if not current_user.pharmacy_id:
            return []
        return query.filter(Pharmacy.id == current_user.pharmacy_id).all()


@router.delete(
    "/{pharmacy_id}", 
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Видалити аптеку",
    responses={
        403: {"description": "Тільки Адмін може видаляти аптеки"},
        404: {"description": "Аптека не знайдена"}
    }
)
def delete_pharmacy(
    pharmacy_id: int, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    pharmacy = db.query(Pharmacy).filter(Pharmacy.id == pharmacy_id).first()
    if not pharmacy:
        raise HTTPException(status_code=404, detail="Pharmacy not found")
    
    # Спроба видалення (може впасти, якщо є залежні дані)
    db.delete(pharmacy)
    db.commit()
    return None


# УПРАВЛІННЯ МІСЦЯМИ ЗБЕРІГАННЯ (Холодильники / Полиці)
@router.post(
    "/locations", 
    response_model=StorageLocationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Створити місце зберігання",
    description="Адмін - де завгодно. Менеджер - тільки у своїй аптеці.",
    responses={
        403: {"description": "Спроба створити локацію в чужій аптеці"},
        404: {"description": "Аптека не знайдена"}
    }
)
def create_storage_location(
    location: StorageLocationCreate, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    pharmacy = db.query(Pharmacy).filter(Pharmacy.id == location.pharmacy_id).first()
    if not pharmacy:
        raise HTTPException(status_code=404, detail="Pharmacy not found")
    
    # Перевірка прав
    if current_user.role != "admin":
        if current_user.role == "pharmacist":
            raise HTTPException(status_code=403, detail="Pharmacists cannot create locations")
        
        # Менеджер може створювати тільки у своїй аптеці
        if location.pharmacy_id != current_user.pharmacy_id:
            raise HTTPException(status_code=403, detail="You can only create locations in your pharmacy")

    db_location = StorageLocation(
        name=location.name,
        description=location.description,
        is_refrigerated=location.is_refrigerated,
        pharmacy_id=location.pharmacy_id
    )
    db.add(db_location)
    db.commit()
    db.refresh(db_location)
    return db_location


@router.get(
    "/locations", 
    response_model=List[StorageLocationResponse],
    summary="Список місць зберігання",
    description="Адмін може фільтрувати по pharmacy_id. Інші бачать тільки свої."
)
def read_storage_locations(
    pharmacy_id: Optional[int] = None, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = db.query(StorageLocation)

    if current_user.role == "admin":
        if pharmacy_id:
            query = query.filter(StorageLocation.pharmacy_id == pharmacy_id)
    else:
        # прив'язка до СВОЄЇ аптеки
        if not current_user.pharmacy_id:
            return []
        query = query.filter(StorageLocation.pharmacy_id == current_user.pharmacy_id)

    return query.all()


@router.delete(
    "/locations/{location_id}", 
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Видалити місце зберігання",
    responses={
        403: {"description": "Чужа аптека"},
        404: {"description": "Локація не знайдена"}
    }
)
def delete_storage_location(
    location_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    location = db.query(StorageLocation).filter(StorageLocation.id == location_id).first()
    if not location:
        raise HTTPException(status_code=404, detail="Location not found")
    
    # Перевірка прав
    if current_user.role != "admin":
        if current_user.pharmacy_id != location.pharmacy_id:
            raise HTTPException(status_code=403, detail="Not enough privileges to manage this pharmacy")

    db.delete(location)
    db.commit()
    return None