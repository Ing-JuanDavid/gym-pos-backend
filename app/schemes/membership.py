from pydantic import BaseModel
from datetime import date


class MembershipCreate(BaseModel):
    status: bool | None = True
    customer_id: int
    plan_id: int


class MembershipUpdate(BaseModel):
    status: bool | None = None
    start_date: date | None = None
    end_date: date | None = None
    customer_id: int | None = None
    plan_id: int | None = None


class MembershipPublic(MembershipCreate):
    start_date: date
    end_date: date | None
    membership_id: int
