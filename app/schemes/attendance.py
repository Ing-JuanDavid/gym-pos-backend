from pydantic import BaseModel
from datetime import datetime
from enum import Enum


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


# websocket events

class AttendanceResult(str, Enum):
    CHECK_IN = "CHECK_IN"
    CHECK_OUT = "CHECK_OUT"

    CUSTOMER_NOT_FOUND = "CUSTOMER_NOT_FOUND"

    MEMBERSHIP_NOT_FOUND = "MEMBERSHIP_NOT_FOUND"
    MEMBERSHIP_EXPIRED = "MEMBERSHIP_EXPIRED"

    ALREADY_CHECKED_IN = "ALREADY_CHECKED_IN"

    ERROR = "ERROR"


class AttendanceResponse(BaseModel):
    status: AttendanceResult
    attendance_id: int | None = None
    customer_id: int | None = None
    message: str | None = None
