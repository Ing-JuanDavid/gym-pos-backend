from enum import Enum
from sqlmodel import SQLModel, Field, table, Relationship
from datetime import datetime
from sqlalchemy import Column, DateTime
from enum import Enum


class SaleStatus(str, Enum):
    PAGADA = "PAGADA"
    PARCIAL = "PARCIAL"
    PENDIENTE = "PENDIENTE"


class Sale(SQLModel, table=True):
    sale_id: int | None = Field(primary_key=True, default=None)
    nuip: int
    total: int | None = Field(gt=0, default=None)
    created_at: datetime = Field(sa_column=Column(
        DateTime(timezone=False)), default_factory=datetime.now)
    status: SaleStatus = Field(default=SaleStatus.PENDIENTE)
    customer_id: int = Field(
        foreign_key="customer.customer_id", ondelete="CASCADE")

    details: list["SaleDetail"] = Relationship(
        back_populates="sale", cascade_delete=True)
    payments: list["Payment"] = Relationship(
        back_populates="sale", cascade_delete=True)


class SaleDetail(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    item_type: str  # "membership" o "product"
    item_id: int
    quantity: int = 1
    unit_price: int
    sale_id: int = Field(foreign_key="sale.sale_id", ondelete="CASCADE")

    sale: "Sale" = Relationship(back_populates="details")
