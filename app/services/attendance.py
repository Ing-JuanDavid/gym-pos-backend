
from app.database import Session, SessionDep
from fastapi import Depends
from typing import Annotated
from datetime import datetime, time
from app.models.attendance import Attendance
from app.models.customers import Customer
from app.models.membership import Membership
from app.models.plan import Plan
from app.services.customer import CustomerService, CustomerServiceDep
from app.services.membership import MembershipService, MembershipServiceDep
from app.schemes.attendance import AttendancePublic, AttendanceResponse, AttendanceResult, AttendanceListItem
from sqlmodel import select, desc
from app.utilities.exceptions import not_found, conflict

from app.database import Session, SessionDep


class AttendanceService:
    def __init__(self, session: Session, customer_service: CustomerService, membership_service: MembershipService):
        self.session = session
        self.customer_service = customer_service
        self.membership_service = membership_service

    # CREATE (Check-in)
    def check_in(self, nuip: int) -> AttendancePublic:

        #  check the customer and membership
        db_customer = self.customer_service.get_customer(nuip)

        if not db_customer:
            raise not_found("customer")

        active_membership = self.customer_service.get_active_membership(
            db_customer.memberships)

        if not active_membership:
            raise conflict("no membership activated yet")

        # check current attendance
        if (self.get_current_attendance(db_customer)):
            raise conflict("user already attended")

        attendance = Attendance(
            customer_id=db_customer.customer_id,
            membership_id=active_membership.membership_id,
        )
        self.session.add(attendance)
        self.session.commit()
        self.session.refresh(attendance)
        return attendance

    # UPDATE (Check-out)
    def check_out(self, nuip: int) -> AttendancePublic:

        db_customer = self.customer_service.get_customer(nuip)

        if not db_customer:
            raise not_found("customer")

        db_attendance = self.get_current_attendance(db_customer)

        if not db_attendance:
            raise conflict("user hasn't attended yet")

        db_attendance.check_out = datetime.now()
        self.session.add(db_attendance)
        self.session.commit()
        self.session.refresh(db_attendance)
        return db_attendance

    # READ (por id)
    def get_attendance(self, attendance_id: int) -> AttendancePublic | None:
        return self.session.get(Attendance, attendance_id)

    # READ (historial por cliente)
    def list_customer_attendances(self, nuip: int) -> list[AttendancePublic]:

        db_customer = self.customer_service.get_customer(nuip)

        if not db_customer:
            raise not_found("customer")

        statement = select(Attendance).where(
            Attendance.customer_id == db_customer.customer_id).order_by(desc(Attendance.check_in))
        return list(self.session.exec(statement))

    # READ (ALL)
    def list_attendances(self) -> list[AttendancePublic]:
        statement = select(Attendance).order_by(desc(Attendance.check_in))
        return list(self.session.exec(statement))

    from sqlmodel import select

    def list_attendances_items(self) -> list[AttendanceListItem]:

        statement = (
            select(
                Attendance,
                Customer,
                Membership,
                Plan
            )
            .join(
                Membership,
                Attendance.membership_id == Membership.membership_id
            )
            .join(
                Customer,
                Attendance.customer_id == Customer.customer_id
            )
            .join(
                Plan,
                Membership.plan_id == Plan.plan_id
            )
            .order_by(
                Attendance.check_in.desc()
            )
        )

        results = self.session.exec(statement).all()

        return [
            AttendanceListItem(
                attendance_id=attendance.id,

                nuip=customer.nuip,
                customer_name=f"{customer.first_name} {customer.last_name}",

                membership_name=plan.name,

                check_in=attendance.check_in,
                check_out=attendance.check_out,

                status=(
                    "ACTIVE"
                    if attendance.check_out is None
                    else "FINISHED"
                )
            )
            for attendance, customer, membership, plan in results
        ]

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

    # CREATE (Check-in)
    def register_attendance(self, nuip: int) -> AttendanceResponse:

        response = AttendanceResponse(status=AttendanceResult.ERROR)
        self.session.expire_all()

        #  check the customer and membership
        db_customer = self.customer_service.get_customer(nuip)

        if not db_customer:
            response.status = AttendanceResult.CUSTOMER_NOT_FOUND
            return response

        response.customer_id = db_customer.customer_id

        active_membership = self.customer_service.get_active_membership(
            db_customer.memberships)

        if not active_membership:
            response.status = AttendanceResult.MEMBERSHIP_NOT_FOUND
            return response

        # check current attendance
        if (self.get_current_attendance(db_customer)):
            response.attendance_id = self.check_out(nuip).id
            response.status = AttendanceResult.CHECK_OUT
            return response

        attendance = Attendance(
            customer_id=db_customer.customer_id,
            membership_id=active_membership.membership_id,
        )
        self.session.add(attendance)
        self.session.commit()
        self.session.refresh(attendance)

        response.status = AttendanceResult.CHECK_IN
        response.attendance_id = attendance.id

        return response


def get_attendance_service(session: SessionDep, customer_service: CustomerServiceDep, membership_service: MembershipServiceDep) -> AttendanceService:
    return AttendanceService(
        session=session,
        customer_service=customer_service,
        membership_service=membership_service
    )


AttendanceServiceDep = Annotated[AttendanceService, Depends(
    get_attendance_service)]
