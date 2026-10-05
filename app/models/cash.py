from sqlmodel import SQLModel, Field, table
from datetime import datetime


class CashSession(SQLModel, table=True):
    session_id: int | None = Field(primary_key=True, default=None)
    opening_balance: int = Field(default=0)
    closing_balance: int | None = Field(default=None)
    opened_at: datetime = Field(default_factory=datetime.now)
    closed_at: datetime | None = Field(default=None)
