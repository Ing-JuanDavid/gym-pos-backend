from sqlmodel import SQLModel, Field, table
from datetime import datetime
from sqlalchemy import Column, DateTime
from sqlmodel import Relationship
from app.models.cash_movement import CashMovement


class CashSession(SQLModel, table=True):
    session_id: int | None = Field(primary_key=True, default=None)
    opening_balance: int = Field(default=0)
    closing_balance: int | None = Field(default=None)
    total_balance: int | None = Field(default=0)
    difference: int | None = Field(default=0)
    opened_at: datetime = Field(
        default_factory=datetime.now, sa_column=Column(DateTime(timezone=False)))
    closed_at: datetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=False)))

    movements: list["CashMovement"] = Relationship(cascade_delete=True)
