from pydantic import BaseModel, Field
from enum import Enum
from app.models.payment import PaymentMethod


class ItemType(str, Enum):
    PLAN = "PLAN"
    PRODUCTO = "PRODUCTO"


class PaymentCreate(BaseModel):
    payment_method: PaymentMethod
    details: list[PaymentDetail]


class PaymentDetail(BaseModel):
    item_id: int = Field(gt=0)
    item_type: ItemType = Field(default=ItemType.PLAN)
    quantity: int = Field(gt=0)
