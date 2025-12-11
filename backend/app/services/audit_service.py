from sqlalchemy.orm import Session
from app.db.models import AuditLog
from typing import Any, Dict, Optional

def log_action(
    db: Session,
    user_id: Optional[int],
    action: str,
    details: Dict[str, Any] = None
):
    """
    Функція для запису дій у журнал аудиту.
    """
    new_log = AuditLog(
        user_id=user_id,
        action=action,
        details=details
    )
    db.add(new_log)