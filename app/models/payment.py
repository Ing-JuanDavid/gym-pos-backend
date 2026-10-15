from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from datetime import datetime

from enum import Enum


class PaymentMethod(str, Enum):
    EFECTIVO = "EFECTIVO"
    TRANSFERENCIA = "TRANSFERENCIA"


class Payment(SQLModel, table=True):
    payment_id: int | None = Field(default=None, primary_key=True)
    amount: int
    payment_method: PaymentMethod
    created_at: datetime = Field(sa_column=Column(DateTime(timezone=False)),
                                 default_factory=datetime.now)

    sale_id: int = Field(foreign_key="sale.sale_id")
    sale: "Sale" = Relationship(back_populates="payments")
