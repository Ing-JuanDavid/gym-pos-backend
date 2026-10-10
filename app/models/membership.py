from sqlmodel import SQLModel, table, Field, Relationship
from datetime import date
from typing import Optional


class Membership(SQLModel, table=True):
    membership_id: int | None = Field(primary_key=True, default=None)
    status: bool = Field(default=True)
    start_date: date | None = Field(default=None)
    end_date: date | None = Field(default=None)
    customer_id: int = Field(foreign_key="customer.customer_id")
    plan_id: int = Field(foreign_key="plan.plan_id")

    customer: Optional["Customer"] = Relationship(back_populates="memberships")
