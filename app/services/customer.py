from app.database import Session, SessionDep
from sqlmodel import select
from app.models.customers import Customer
from app.models.plan import Plan
from app.models.attendance import Attendance
from app.models.membership import Membership
from app.utilities.exceptions import not_found, invalid
from fastapi import Depends
from typing import Annotated

from app.schemes.customer import CustomerCreate, CustomerUpdate, CustomerPublic
from sqlalchemy import func
from sqlmodel import select


class CustomerService:
    def __init__(self, session: Session):
        self.session = session

    def get_customer_id(self, customer_id: int) -> Customer | None:
        return self.session.get(Customer, customer_id)

    def get_customer(self, nuip: int) -> Customer | None:
        statement = select(Customer).where(Customer.nuip == nuip)
        return self.session.exec(statement).first()

    def create_customer(self, customer: CustomerCreate) -> CustomerPublic:

        db_customer = self.get_customer(customer.nuip)

        if db_customer:
            raise invalid("customer")

        db_customer = Customer.model_validate(customer)

        self.session.add(db_customer)
        self.session.commit()
        self.session.refresh(db_customer)

        return db_customer

    def read_customers(self) -> list[CustomerPublic]:

        last_attendance_subquery = (
            select(
                Attendance.customer_id,
                func.max(Attendance.check_in).label("last_attendance")
            )
            .group_by(Attendance.customer_id)
            .subquery()
        )

        query = (
            select(
                Customer,
                Plan.name.label("membership_name"),
                last_attendance_subquery.c.last_attendance,
            )
            .outerjoin(
                Membership,
                (Membership.customer_id == Customer.customer_id)
                & (Membership.status == True)
            )
            .outerjoin(
                Plan,
                Plan.plan_id == Membership.plan_id
            )
            .outerjoin(
                last_attendance_subquery,
                last_attendance_subquery.c.customer_id == Customer.customer_id
            )
        )

        rows = self.session.exec(query).all()

        return [
            CustomerPublic(
                customer_id=customer.customer_id,
                nuip=customer.nuip,
                first_name=customer.first_name,
                last_name=customer.last_name,
                phone=customer.phone,
                email=customer.email,
                sex=customer.sex,
                birth=customer.birth,
                membership_name=membership_name,
                last_attendance=last_attendance,
            )
            for customer, membership_name, last_attendance in rows
        ]

    def read_customer(self, customer_id: int) -> CustomerPublic | None:

        last_attendance_subquery = (
            select(
                Attendance.customer_id,
                func.max(Attendance.check_in).label("last_attendance")
            )
            .group_by(Attendance.customer_id)
            .subquery()
        )

        query = (
            select(
                Customer,
                Plan.name.label("membership_name"),
                last_attendance_subquery.c.last_attendance,
            )
            .where(Customer.customer_id == customer_id)
            .outerjoin(
                Membership,
                (Membership.customer_id == Customer.customer_id)
                & (Membership.status == True)
            )
            .outerjoin(
                Plan,
                Plan.plan_id == Membership.plan_id
            )
            .outerjoin(
                last_attendance_subquery,
                last_attendance_subquery.c.customer_id == Customer.customer_id
            )
        )

        row = self.session.exec(query).first()

        if not row:
            return None

        customer, membership_name, last_attendance = row

        return CustomerPublic(
            customer_id=customer.customer_id,
            nuip=customer.nuip,
            first_name=customer.first_name,
            last_name=customer.last_name,
            phone=customer.phone,
            email=customer.email,
            sex=customer.sex,
            birth=customer.birth,
            membership_name=membership_name,
            last_attendance=last_attendance,
        )

    # update

    def find_customer(self, nuip: int) -> Customer | None:
        statement = select(Customer).where(Customer.nuip == nuip)
        return self.session.exec(statement).first()

    def update_customer(self, nuip: int, customer: CustomerUpdate) -> CustomerPublic:
        db_customer = self.find_customer(nuip)

        if not db_customer:
            raise not_found("customer")

        customer_data = customer.model_dump(exclude_unset=True)

        db_customer.sqlmodel_update(customer_data)
        self.session.commit()
        self.session.refresh(db_customer)
        return db_customer

    # delete
    def delete_customer(self, nuip: int):
        db_customer = self.find_customer(nuip)

        if not db_customer:
            raise not_found("customer")

        self.session.delete(db_customer)
        self.session.commit()

    def get_active_membership(self, memberships: list[Membership]) -> Membership | None:
        for m in memberships:
            if m.status:
                return m

        return None


def get_customer_Service(session: SessionDep) -> CustomerService:
    return CustomerService(
        session=session
    )


CustomerServiceDep = Annotated[CustomerService, Depends(get_customer_Service)]
