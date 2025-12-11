from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Any, Optional

from app.db.database import get_db
from app.db.models import AuditLog, User, Sale, Alert, Pharmacy, IoTDevice, StorageLocation
from app.api.deps import get_current_admin, get_current_user # Додали get_current_user

router = APIRouter()

# TO-DO ПЕРЕНЕСТИ СХЕМУ
from pydantic import BaseModel
from datetime import datetime

class AuditLogResponse(BaseModel):
    id: int
    user_id: int | None
    action: str
    details: Any
    created_at: datetime
    class Config:
        from_attributes = True

@router.get("/audit-logs", response_model=List[AuditLogResponse])
def read_audit_logs(
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    """
    Перегляд журналу дій. Останні 100 записів.
    """
    return db.query(AuditLog).order_by(AuditLog.created_at.desc()).limit(limit).all()

@router.get("/dashboard-stats")
def get_dashboard_stats(
    pharmacy_id: Optional[int] = None, # Фільтр для адміна
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user) # Пускаємо і менеджерів
):
    """
    Універсальний дашборд.
    - Адмін: Бачить все. Може передати pharmacy_id для фільтрації.
    - Менеджер: Бачить статистику ТІЛЬКИ своєї аптеки (ігнорує параметр pharmacy_id).
    """
    
    target_pharmacy_id = None

    if current_user.role == "admin":
        target_pharmacy_id = pharmacy_id 
    elif current_user.role == "manager":
        target_pharmacy_id = current_user.pharmacy_id
    else:
        raise HTTPException(status_code=403, detail="Not enough privileges")

    # --- ПІДГОТОВКА ЗАПИТІВ ---
    sales_query = db.query(
        func.count(Sale.id).label("count"),
        func.sum(Sale.total_amount).label("revenue")
    )
    
    alerts_query = db.query(func.count(Alert.id)).select_from(Alert)\
        .join(IoTDevice).join(StorageLocation)\
        .filter(Alert.is_resolved == False)

    staff_query = db.query(func.count(User.id))

    if target_pharmacy_id:
        sales_query = sales_query.filter(Sale.pharmacy_id == target_pharmacy_id)
        
        alerts_query = alerts_query.filter(StorageLocation.pharmacy_id == target_pharmacy_id)
        
        staff_query = staff_query.filter(User.pharmacy_id == target_pharmacy_id)

    sales_result = sales_query.first()
    active_alerts = alerts_query.scalar()
    staff_count = staff_query.scalar()

    return {
        "pharmacy_filter": target_pharmacy_id if target_pharmacy_id else "All Network",
        "total_sales_orders": sales_result.count or 0,
        "total_revenue": float(sales_result.revenue or 0),
        "active_alerts": active_alerts or 0,
        "total_staff": staff_count or 0
    }