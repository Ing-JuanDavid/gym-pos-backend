from sqlmodel import SQLModel, table, Field
from sqlalchemy import Column, DateTime
from datetime import datetime
from app.models.payment import PaymentMethod
from enum import Enum


class MovementType(str, Enum):
    ENTRADA = "ENTRADA"
    SALIDA = "SALIDA"


class CashMovement(SQLModel, table=True):
    movement_id: int | None = Field(default=None, primary_key=True)
    amount: int
    payment_type: PaymentMethod
    movement_type: MovementType
    create_at: datetime | None = Field(sa_column=Column(DateTime(timezone=False)),
                                       default_factory=datetime.now)
    session_id: int = Field(
        foreign_key="cashsession.session_id", ondelete="CASCADE")
