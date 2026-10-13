from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from datetime import datetime

from enum import Enum


class PaymentMethod(str, Enum):
    EFECTIVO = "EFECTIVO"
    TRANSFERENCIA = "TRANSFERENCIA"


class Payment(SQLModel, table=True):
    payment_id: int | None = Field(default=None, primary_key=True)
    customer_id: int = Field(foreign_key="customer.customer_id")
    amount: int
    payment_method: PaymentMethod
    created_at: datetime = Field(sa_column=Column(DateTime(timezone=False)),
                                 default_factory=datetime.now)

    details: list["PaymentDetail"] = Relationship(back_populates="payment")


class PaymentDetail(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    payment_id: int = Field(foreign_key="payment.payment_id")
    item_type: str  # "membership" o "product"
    item_id: int
    quantity: int = 1
    unit_price: int

    payment: Payment = Relationship(back_populates="details")


class Product(SQLModel, table=True):
    product_id: int | None = Field(default=None, primary_key=True)
    name: str
    price: int
    stock: int = 0
