from fastapi import APIRouter, Depends, HTTPException, status, Body
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from typing import List, Optional, Any

from app.db.database import get_db
from app.db.models import User, Pharmacy
from app.schemas.auth_schemas import Token
from app.schemas.user_schemas import UserCreate, UserResponse
from app.core.security import verify_password, get_password_hash, create_access_token
from app.api.deps import get_current_user

router = APIRouter()


# ПУБЛІЧНА РЕЄСТРАЦІЯ (Для початкового налаштування!)
@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Реєстрація першого адміністратора",
    description="Цей ендпоінт публічний. Він потрібен для створення адміна.",
    responses={
        400: {"description": "Користувач з таким email вже існує"}
    }
)
def register_initial_admin(user_in: UserCreate, db: Session = Depends(get_db)):
    """
    Створення користувача без авторизації.
    """
    if db.query(User).filter(User.email == user_in.email).first():
        raise HTTPException(
            status_code=400,
            detail="The user with this email already exists.",
        )
    
    new_user = User(
        email=user_in.email,
        hashed_password=get_password_hash(user_in.password),
        full_name=user_in.full_name,
        role=user_in.role, # Тут можна передати 'admin'
        pharmacy_id=user_in.pharmacy_id,
        is_active=user_in.is_active
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user


# СТВОРЕННЯ СПІВРОБІТНИКІВ (Захищений маршрут)
@router.post(
    "/users",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Створення нового співробітника",
    description="Доступно Адміну та Менеджеру. Менеджер автоматично створює працівника у своїй аптеці.",
    responses={
        403: {"description": "Недостатньо прав (Фармацевт або спроба Менеджера створити Адміна)"},
        404: {"description": "Аптека не знайдена"},
        400: {"description": "Email зайнятий"}
    }
)
def create_employee(
    user_in: UserCreate, 
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    if current_user.role == "pharmacist":
        raise HTTPException(status_code=403, detail="Pharmacists cannot create users")

    if current_user.role == "manager":
        if user_in.role in ["admin", "manager"]:
             raise HTTPException(status_code=403, detail="Managers can only create Pharmacists")
        
        # !ВАЖЛИВО: Менеджер не може обрати аптеку. Примусово ставимо його аптеку.
        target_pharmacy_id = current_user.pharmacy_id
    
    elif current_user.role == "admin":
        target_pharmacy_id = user_in.pharmacy_id

    if target_pharmacy_id:
        pharmacy = db.query(Pharmacy).filter(Pharmacy.id == target_pharmacy_id).first()
        if not pharmacy:
            raise HTTPException(status_code=404, detail="Pharmacy not found")

    if db.query(User).filter(User.email == user_in.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")

    new_user = User(
        email=user_in.email,
        hashed_password=get_password_hash(user_in.password),
        full_name=user_in.full_name,
        role=user_in.role,
        pharmacy_id=target_pharmacy_id, # Використовуємо обчислене значення
        is_active=True
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user



# ВХІД В СИСТЕМУ
@router.post(
    "/login",
    response_model=Token,
    summary="Вхід (Отримання токена)",
    responses={
        401: {"description": "Невірний логін або пароль"},
        400: {"description": "Користувач неактивний"}
    }
)
def login_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == form_data.username).first()
    
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")

    access_token = create_access_token(subject=user.email)
    return {"access_token": access_token, "token_type": "bearer"}



# ВИДАЛЕННЯ КОРИСТУВАЧА
@router.delete(
    "/users/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Видалення користувача",
    description="Адмін видаляє будь-кого. Менеджер - тільки своїх. Себе видалити не можна.",
    responses={
        403: {"description": "Заборонено (Чужа аптека або спроба видалити керівника)"},
        404: {"description": "Користувач не знайдений"}
    }
)
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    user_to_delete = db.query(User).filter(User.id == user_id).first()
    if not user_to_delete:
        raise HTTPException(status_code=404, detail="User not found")

    if user_to_delete.id == current_user.id:
        raise HTTPException(status_code=400, detail="You cannot delete yourself")

    # Логіка прав
    if current_user.role == "manager":
        if user_to_delete.pharmacy_id != current_user.pharmacy_id:
            raise HTTPException(status_code=403, detail="You can only manage users in your pharmacy")
        if user_to_delete.role in ["admin", "manager"]:
            raise HTTPException(status_code=403, detail="You cannot delete admins or managers")
    
    elif current_user.role == "pharmacist":
        raise HTTPException(status_code=403, detail="Not enough privileges")
    
    # Адмін проходить без перевірок

    db.delete(user_to_delete)
    db.commit()
    return None


# 5. ОТРИМАННЯ СПИСКУ КОРИСТУВАЧІВ
@router.get(
    "/users",
    response_model=List[UserResponse],
    summary="Список співробітників",
    description="Менеджер бачить тільки свою аптеку. Адмін - усіх.",
    responses={
        403: {"description": "Фармацевтам доступ заборонено"}
    }
)
def read_users(
    pharmacy_id: Optional[int] = None, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = db.query(User)

    if current_user.role == "admin":
        if pharmacy_id:
            query = query.filter(User.pharmacy_id == pharmacy_id)
    
    elif current_user.role == "manager":
        # Жорстка фільтрація: Тільки своя аптека
        query = query.filter(User.pharmacy_id == current_user.pharmacy_id)
    
    else:
        raise HTTPException(status_code=403, detail="Not enough privileges")

    return query.all()