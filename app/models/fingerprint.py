from sqlmodel import SQLModel, table, Field, Relationship
from datetime import date


class Fingerprint(SQLModel, table=True):
    id: int | None = Field(primary_key=True, default=None)
    print_id: int
    status: bool | None = Field(default=True)
    register_date: date | None = Field(default_factory=date.today)
    customer_id: int = Field(
        foreign_key="customer.customer_id", ondelete="CASCADE")

    customer: "Customer" = Relationship()
