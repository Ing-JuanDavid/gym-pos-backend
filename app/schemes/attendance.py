from pydantic import BaseModel
from datetime import datetime


class AttendanceCreate(BaseModel):
    nuip: int


class AttendanceUpdate(BaseModel):
    check_out: datetime | None = None


class AttendancePublic(BaseModel):
    id: int
    check_in: datetime
    check_out: datetime | None
    customer_id: int
    membership_id: int
