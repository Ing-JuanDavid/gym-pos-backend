from pydantic import BaseModel, Field


class PlanCreate(BaseModel):
    name: str = Field(max_length=50)
    description: str = Field(max_length=100)
    duration: int = Field(gt=0)
    amount: int


class PlanUpdate(BaseModel):
    name: str | None = Field(max_length=50, default=None)
    description: str | None = Field(max_length=100, default=None)
    duration: int | None = Field(gt=0, default=None)
    amount: int | None = Field(default=None)


class PlanPublic(PlanCreate):
    plan_id: int
