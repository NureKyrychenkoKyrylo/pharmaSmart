from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional

from app.db.database import get_db
from app.db.models import Sale, SaleItem, Batch, User, Pharmacy, StorageLocation
from app.schemas.sales_schemas import SaleCreate, SaleResponse
from app.api.deps import get_current_user
from app.services.audit_service import log_action

router = APIRouter()

@router.post(
    "/",
    response_model=SaleResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Оформлення продажу (Чек)",
    description="Фармацевт продає ліки. Система списує їх зі складу та розраховує суму."
)
def create_sale(
    sale_data: SaleCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if not current_user.pharmacy_id:
        raise HTTPException(status_code=403, detail="User must be assigned to a pharmacy to sell")

    new_sale = Sale(
        pharmacy_id=current_user.pharmacy_id,
        seller_id=current_user.id,
        total_amount=0.0,
        status="completed"
    )
    db.add(new_sale)
    db.flush() # Щоб отримати ID нового чека (new_sale.id)

    total_sum = 0.0
    items_summary = [] # Для логу аудиту

    # Обробляємо кожну позицію в чеку
    for item in sale_data.items:
        # Шукаємо партію ліків
        batch = db.query(Batch).filter(Batch.id == item.batch_id).first()
        
        if not batch:
            db.rollback()
            raise HTTPException(status_code=404, detail=f"Batch {item.batch_id} not found")

        location = db.query(StorageLocation).filter(StorageLocation.id == batch.storage_location_id).first()
        if location.pharmacy_id != current_user.pharmacy_id:
             db.rollback()
             raise HTTPException(status_code=403, detail=f"Batch {batch.batch_number} belongs to another pharmacy")

        if batch.current_quantity < item.quantity:
             db.rollback()
             raise HTTPException(
                 status_code=400, 
                 detail=f"Not enough stock for Batch {batch.batch_number}. Available: {batch.current_quantity}"
             )
        
        # Логіка списання
        batch.current_quantity -= item.quantity
        
        item_price = 100.00 
        
        cost = item_price * item.quantity
        total_sum += cost

        db_item = SaleItem(
            sale_id=new_sale.id,
            batch_id=batch.id,
            quantity=item.quantity,
            price_at_moment=item_price
        )
        db.add(db_item)
        
        items_summary.append({
            "batch": batch.batch_number, 
            "qty": item.quantity, 
            "subtotal": cost
        })

    new_sale.total_amount = total_sum
    
    log_action(
        db,
        user_id=current_user.id,
        action="SALE_CREATED",
        details={
            "sale_id": new_sale.id,
            "total": total_sum,
            "items": items_summary
        }
    )

    db.commit()
    db.refresh(new_sale)
    return new_sale

@router.get(
    "/",
    response_model=List[SaleResponse],
    summary="Історія продажів",
    description="Адмін бачить все. Менеджер - тільки свою аптеку."
)
def read_sales(
    pharmacy_id: Optional[int] = None,
    limit: int = 100,
    skip: int = 0,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Юзаєм joinedload, щоб одразу підтягнути список товарів (items) у чеку
    query = db.query(Sale).options(joinedload(Sale.items))

    if current_user.role == "admin":
        if pharmacy_id:
            query = query.filter(Sale.pharmacy_id == pharmacy_id)
    else:
        if not current_user.pharmacy_id:
            return []
        query = query.filter(Sale.pharmacy_id == current_user.pharmacy_id)

    return query.order_by(Sale.created_at.desc()).offset(skip).limit(limit).all()

@router.get(
    "/{sale_id}",
    response_model=SaleResponse,
    summary="Деталі чека",
    responses={
        404: {"description": "Чек не знайдено"},
        403: {"description": "Чек з чужої аптеки"}
    }
)
def read_sale_detail(
    sale_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    sale = db.query(Sale).options(joinedload(Sale.items)).filter(Sale.id == sale_id).first()
    
    if not sale:
        raise HTTPException(status_code=404, detail="Sale not found")

    if current_user.role != "admin":
        if sale.pharmacy_id != current_user.pharmacy_id:
            raise HTTPException(status_code=403, detail="Access to this sale is forbidden")

    return sale