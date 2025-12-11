from pydantic import BaseModel
from datetime import datetime
from typing import List

class SaleItemCreate(BaseModel):
    batch_id: int
    quantity: int
    price_per_unit: float

class SaleCreate(BaseModel):
    # pharmacy_id та seller_id беремо з ТОКЕНА!!! користувача,
    # тому тут їх передавати не обов'язково
    items: List[SaleItemCreate]

class SaleItemResponse(BaseModel):
    id: int
    batch_id: int
    quantity: int
    price_at_moment: float

    class Config:
        from_attributes = True

class SaleResponse(BaseModel):
    id: int
    pharmacy_id: int
    seller_id: int | None
    total_amount: float
    status: str
    created_at: datetime
    items: List[SaleItemResponse]

    class Config:
        from_attributes = True