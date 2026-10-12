from fastapi import APIRouter, Depends, Query
from app.services.attendance import AttendanceService, AttendanceServiceDep
from app.schemes.attendance import AttendanceCreate, AttendancePublic

router = APIRouter(prefix="/attendances", tags=["attendances"])

# CREATE (Check-in)


@router.post("/checkin", response_model=AttendancePublic)
def check_in(
    data: AttendanceCreate,
    service: AttendanceServiceDep,
    daily_membership: bool = Query(default=False)
):
    return service.check_in(data, daily_membership)

# UPDATE (Check-out)


@router.put("/{attendance_id}/checkout", response_model=AttendancePublic | None)
def check_out(
    attendance_id: int,
    service: AttendanceServiceDep
):
    return service.check_out(attendance_id)

# READ (por id)


@router.get("/{attendance_id}", response_model=AttendancePublic | None)
def get_attendance(
    attendance_id: int,
    service: AttendanceServiceDep
):
    return service.get_attendance(attendance_id)

# READ (historial por cliente)


@router.get("/customer/{customer_id}", response_model=list[AttendancePublic])
def list_customer_attendances(
    customer_id: int,
    service: AttendanceServiceDep
):
    return service.list_customer_attendances(customer_id)

# READ (todos)


@router.get("/", response_model=list[AttendancePublic])
def list_attendances(
    service: AttendanceServiceDep
):
    return service.list_attendances()

# DELETE


@router.delete("/{attendance_id}", response_model=bool)
def delete_attendance(
    attendance_id: int,
    service: AttendanceServiceDep
):
    return service.delete_attendance(attendance_id)
