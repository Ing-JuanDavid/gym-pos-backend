from sqlalchemy import Column, DateTime
from sqlmodel import SQLModel, table, Field, Relationship
from datetime import datetime
from typing import Optional


class Attendance(SQLModel, table=True):
    id: int | None = Field(primary_key=True, default=None)
    check_in: datetime | None = Field(
        sa_column=Column(DateTime(timezone=False)),
        default_factory=datetime.now
    )
    check_out: datetime | None = Field(
        sa_column=Column(DateTime(timezone=False)),
        default=None
    )
    customer_id: int = Field(
        foreign_key="customer.customer_id", ondelete="CASCADE")
    membership_id: int = Field(foreign_key="membership.membership_id")

    customer: "Customer" = Relationship(
        back_populates="attendances"
    )

    membership: "Membership" = Relationship(
        back_populates="attendances"
    )
