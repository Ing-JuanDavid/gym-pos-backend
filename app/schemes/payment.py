from pydantic import BaseModel, Field
from enum import Enum
from app.models.payment import PaymentMethod
from datetime import datetime


class ItemType(str, Enum):
    PLAN = "PLAN"
    PRODUCTO = "PRODUCTO"


class PaymentCreate(BaseModel):
    payment_method: PaymentMethod
    amount: int = Field(gt=0)


class PaymentDetail(BaseModel):
    item_id: int = Field(gt=0)
    item_type: ItemType = Field(default=ItemType.PLAN)
    quantity: int = Field(gt=0)


class PaymentPublic(BaseModel):
    payment_id: int
    amount: int
    payment_method: PaymentMethod
    created_at: datetime
