from sqlmodel import SQLModel, table, Field
from datetime import date


class Membership(SQLModel, table=True):
    membership_id: int | None = Field(primary_key=True, default=None)
    status: bool = Field(default=True)
    start_date: date
    end_date: date | None = Field(default=None)
    customer_id: int = Field(foreign_key="customer.customer_id")
    plan_id: int = Field(foreign_key="plan.plan_id")
