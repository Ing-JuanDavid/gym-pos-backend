from pydantic import BaseModel, Field
from enum import Enum
from app.models.payment import PaymentMethod
from datetime import datetime
from app.models.sale import SaleStatus, SaleDetail


class ItemType(str, Enum):
    PLAN = "PLAN"
    PRODUCTO = "PRODUCTO"


class SaleCreate(BaseModel):
    nuip: int
    details: list[PaymentDetail]


class SaleResume(BaseModel):
    sale_id: int
    nuip: int
    total: int
    created_at: datetime
    status: SaleStatus
    pending_amout: int
    details: list[SaleDetail]


class PaymentDetail(BaseModel):
    item_id: int = Field(gt=0)
    item_type: ItemType = Field(default=ItemType.PLAN)
    quantity: int = Field(gt=0)
