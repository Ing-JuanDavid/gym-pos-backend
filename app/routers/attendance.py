from fastapi import APIRouter, Depends, Query
from app.services.attendance import AttendanceService, AttendanceServiceDep
from app.services.customer import CustomerService, CustomerServiceDep
from app.schemes.attendance import AttendanceCreate, AttendancePublic
from app.utilities.exceptions import not_found

router = APIRouter(prefix="/attendances", tags=["attendances"])

# CREATE (Check-in)


@router.post("/customer/{nuip}/checkin", response_model=AttendancePublic)
def check_in(
    nuip: int,
    service: AttendanceServiceDep
):
    return service.check_in(nuip)

# UPDATE (Check-out)


@router.patch("/customer/{nuip}/checkout", response_model=AttendancePublic)
def check_out(
    nuip: int,
    service: AttendanceServiceDep
):
    return service.check_out(nuip)

# READ (por id)


@router.get("/{attendance_id}", response_model=AttendancePublic | None)
def get_attendance(
    attendance_id: int,
    service: AttendanceServiceDep
):
    return service.get_attendance(attendance_id)

# READ (historial por cliente)


@router.get("/current/customer/{nuip}", response_model=AttendancePublic | None)
async def get_pending_attendance(nuip: int, service: AttendanceServiceDep, customer_service: CustomerServiceDep):
    db_customer = customer_service.get_customer(nuip)

    if not db_customer:
        raise not_found("customer")

    return service.get_current_attendance(db_customer)


@router.get("/customer/{nuip}", response_model=list[AttendancePublic])
def list_customer_attendances(
    nuip: int,
    service: AttendanceServiceDep
):
    return service.list_customer_attendances(nuip)

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
