from sqlmodel import SQLModel, table, Field


class Plan(SQLModel, table=True):
    plan_id: int | None = Field(primary_key=True, default=None)
    name: str = Field(max_length=50)
    description: str = Field(max_length=100)
    duration: int = Field(gt=0)
    amount: int
