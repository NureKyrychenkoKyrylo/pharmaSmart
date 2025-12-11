from pydantic import BaseModel, EmailStr
from datetime import datetime

# Базова схема (спільні поля)
class UserBase(BaseModel):
    email: EmailStr
    full_name: str
    role: str  # 'admin', 'manager', 'pharmacist'
    pharmacy_id: int | None = None
    is_active: bool = True

# Що надсилають при реєстрації (тут є пароль)
class UserCreate(UserBase):
    password: str

# Що віддаємо клієнту (тут НЕМАЄ пароля, але є ID)
class UserResponse(UserBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True  # Дозволяє читати дані прямо з ORM моделі