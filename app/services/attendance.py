
from app.database import Session, SessionDep
from fastapi import Depends
from typing import Annotated
from datetime import datetime, time
from app.models.attendance import Attendance
from app.models.customers import Customer
from app.services.customer import CustomerService, CustomerServiceDep
from app.services.membership import MembershipService, MembershipServiceDep
from app.schemes.attendance import AttendanceCreate, AttendanceUpdate, AttendancePublic
from sqlmodel import select, desc
from app.utilities.exceptions import not_found, conflict

from app.database import Session, SessionDep


class AttendanceService:
    def __init__(self, session: Session, customer_service: CustomerService, membership_service: MembershipService):
        self.session = session
        self.customer_service = customer_service
        self.membership_service = membership_service

    # CREATE (Check-in)
    def check_in(self, data: AttendanceCreate, daily_membership: bool = False) -> AttendancePublic:
        DAILY_MEMBERSHIP_ID = 1

        #  check the customer and membership
        db_customer = self.customer_service.get_customer_id(data.customer_id)

        if not db_customer:
            raise not_found("customer")

        membership_id = None

        if daily_membership:
            membership_id = DAILY_MEMBERSHIP_ID
        else:
            active_membership = self.customer_service.get_active_membership(
                db_customer.memberships)

            if not active_membership:
                raise conflict("no membership activated yet")

            membership_id = active_membership.membership_id

        # check current attendance
        if (self.get_current_attendance(db_customer)):
            raise conflict("user already attended")

        attendance = Attendance(
            customer_id=data.customer_id,
            membership_id=membership_id,
        )
        self.session.add(attendance)
        self.session.commit()
        self.session.refresh(attendance)
        return attendance

    # UPDATE (Check-out)
    def check_out(self, attendance_id: int) -> AttendancePublic | None:
        db_attendance = self.session.get(Attendance, attendance_id)
        if not db_attendance:
            return None

        db_attendance.check_out = datetime.now()
        self.session.add(db_attendance)
        self.session.commit()
        self.session.refresh(db_attendance)
        return db_attendance

    # READ (por id)
    def get_attendance(self, attendance_id: int) -> AttendancePublic | None:
        return self.session.get(Attendance, attendance_id)

    # READ (historial por cliente)
    def list_customer_attendances(self, customer_id: int) -> list[AttendancePublic]:
        statement = select(Attendance).where(
            Attendance.customer_id == customer_id).order_by(desc(Attendance.check_in))
        return list(self.session.exec(statement))

    # READ (todos)
    def list_attendances(self) -> list[AttendancePublic]:
        statement = select(Attendance)
        return list(self.session.exec(statement))

    # DELETE
    def delete_attendance(self, attendance_id: int) -> bool:
        db_attendance = self.get_attendance(attendance_id)
        if not db_attendance:
            return False
        self.session.delete(db_attendance)
        self.session.commit()
        return True

    def get_current_attendance(self, customer: Customer) -> Attendance | None:
        today = datetime.now().date()
        start_of_day = datetime.combine(today, time.min)
        end_of_day = datetime.combine(today, time.max)
        statement = select(Attendance).where(
            Attendance.customer_id == customer.customer_id,
            Attendance.check_in > start_of_day,
            Attendance.check_in < end_of_day,
            Attendance.check_out == None
        )

        db_attendance = self.session.exec(statement).first()
        return db_attendance


def get_attendance_service(session: SessionDep, customer_service: CustomerServiceDep, membership_service: MembershipServiceDep) -> AttendanceService:
    return AttendanceService(
        session=session,
        customer_service=customer_service,
        membership_service=membership_service
    )


AttendanceServiceDep = Annotated[AttendanceService, Depends(
    get_attendance_service)]


# al crear asistencia, verificar que el usuario no tenga una asistencia ese dia*
# al egnerar una asistencia si es por membersia diaria, generar un movimiento de pago, si es por membreia borrar un dia
#  al crera un anueva membresia generar el movimiento
# busccar un mecanismo para
