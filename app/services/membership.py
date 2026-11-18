from sqlmodel import select, desc
from app.database import Session, SessionDep
from app.models.plan import Plan
from app.models.customers import Customer
from app.models.membership import Membership
from app.services.customer import CustomerService, CustomerServiceDep
from app.services.plan import PlanService, PlanServiceDep
from app.schemes.membership import MembershipCreate, MembershipUpdate, MembershipPublic
from app.utilities.exceptions import not_found, conflict
from typing import Annotated
from fastapi import Depends
from datetime import date, timedelta
from app.schemes.membership import MembershipListItem


class MembershipService:
    def __init__(self, session: Session, customer_service: CustomerService, plan_service: PlanService):
        self.session = session
        self.customer_service = customer_service
        self.plan_service = plan_service

    # CREATE
    def create_membership(self, data: MembershipCreate) -> MembershipPublic:

        self.validate_data(data)

        db_plan = self.plan_service.get_plan(data.plan_id)

        if not db_plan:
            raise not_found("plan")

        new_membership = Membership.model_validate(data)
        new_membership.start_date = date.today()
        time_delta = timedelta(days=db_plan.duration-1)
        new_membership.end_date = new_membership.start_date+time_delta
        # set ending date by calculing form duration
        self.session.add(new_membership)
        self.session.commit()
        self.session.refresh(new_membership)
        return new_membership

    # READ (por id)
    def get_membership(self, membership_id: int) -> Membership | None:
        return self.session.get(Membership, membership_id)

    def get_customer_membership(self, nuip: int) -> MembershipPublic:
        db_customer = self.customer_service.get_customer(nuip)

        if not db_customer:
            raise not_found("customer")

        active_membership = self.customer_service.get_active_membership(
            db_customer.memberships)

        return active_membership

    # READ (todos)
    def list_memberships(self, active: bool | None) -> list[MembershipPublic]:
        statement = select(Membership)

        if active != None:
            statement = statement.where(Membership.status == active)

        return list(self.session.exec(statement))

    def list_memberships_detail(
        self,
        active: bool | None
    ) -> list[MembershipListItem]:

        statement = (
            select(
                Membership,
                Customer.first_name,
                Customer.last_name,
                Plan.name
            )
            .join(
                Customer,
                Customer.customer_id == Membership.customer_id
            )
            .join(
                Plan,
                Plan.plan_id == Membership.plan_id
            ).order_by(desc(Membership.start_date))
        )

        if active is not None:
            statement = statement.where(
                Membership.status == active
            )

        rows = self.session.exec(statement).all()

        return [
            MembershipListItem(
                membership_id=membership.membership_id,
                status=membership.status,
                start_date=membership.start_date,
                end_date=membership.end_date,
                customer_id=membership.customer_id,
                customer_name=f"{first_name} {last_name}",
                plan_id=membership.plan_id,
                plan_name=plan_name
            )
            for membership, first_name, last_name, plan_name in rows
        ]

    def list_memberships(self, active: bool | None) -> list[MembershipPublic]:
        statement = select(Membership)

        if active != None:
            statement = statement.where(Membership.status == active)

        return list(self.session.exec(statement))

    def list_memberships_detail_by_customer(
        self,
        active: bool | None,
        nuip: int
    ) -> list[MembershipListItem]:

        statement = (
            select(
                Membership,
                Customer.first_name,
                Customer.last_name,
                Plan.name
            )
            .join(
                Customer,
                Customer.customer_id == Membership.customer_id
            )
            .join(
                Plan,
                Plan.plan_id == Membership.plan_id
            )
            .where(
                Customer.nuip == nuip
            )
            .order_by(
                desc(Membership.start_date)
            )
        )

        if active is not None:
            statement = statement.where(
                Membership.status == active
            )

        rows = self.session.exec(statement).all()

        if not rows:
            db_customer = self.customer_service.get_customer(nuip)

            if not db_customer:
                raise not_found("customer")

        return [
            MembershipListItem(
                membership_id=membership.membership_id,
                status=membership.status,
                start_date=membership.start_date,
                end_date=membership.end_date,
                customer_id=membership.customer_id,
                customer_name=f"{first_name} {last_name}",
                plan_id=membership.plan_id,
                plan_name=plan_name
            )
            for membership, first_name, last_name, plan_name in rows
        ]

    # UPDATE
    def update_membership(self, membership_id: int, data: MembershipUpdate) -> MembershipPublic:
        db_membership = self.get_membership(membership_id)
        if not db_membership:
            raise not_found("membership")

        updated_data = data.model_dump(exclude_unset=True)
        db_membership.sqlmodel_update(updated_data)
        self.session.commit()
        self.session.refresh(db_membership)
        return db_membership

    # DELETE
    def delete_membership(self, membership_id: int) -> bool:
        db_membership = self.get_membership(membership_id)
        if not db_membership:
            return False
        self.session.delete(db_membership)
        self.session.commit()
        return True

    def validate_data(self, data: MembershipCreate) -> None:

        db_customer = self.customer_service.get_customer_id(data.customer_id)

        if not db_customer:
            raise not_found("customer")

        if self.customer_service.get_active_membership(db_customer.memberships):
            raise conflict("user already has a membership")


def get_membership_service(
    session: SessionDep,
    custoemer_service: CustomerServiceDep,
    plan_service: PlanServiceDep
) -> MembershipService:
    return MembershipService(
        session=session,
        customer_service=custoemer_service,
        plan_service=plan_service
    )


MembershipServiceDep = Annotated[
    MembershipService, Depends(get_membership_service)
]
