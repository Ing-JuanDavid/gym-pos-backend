from sqlmodel import select
from app.database import Session, SessionDep
from app.models.membership import Membership
from app.services.customer import CustomerService, CustomerServiceDep
from app.services.plan import PlanService, PlanServiceDep
from app.schemes.membership import MembershipCreate, MembershipUpdate, MembershipPublic
from app.utilities.exceptions import not_found, invalid, confict
from typing import Annotated
from fastapi import Depends
from datetime import date


class MembershipService:
    def __init__(self, session: Session, customer_service: CustomerService, plan_service: PlanService):
        self.session = session
        self.customer_service = customer_service
        self.plan_service = plan_service

    # CREATE
    def create_membership(self, data: MembershipCreate) -> MembershipPublic:

        self.validate_data(data)
        new_membership = Membership.model_validate(data)
        new_membership.start_date = date.today()
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
    def list_memberships(self) -> list[MembershipPublic]:
        statement = select(Membership)
        return list(self.session.exec(statement))

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

        if not self.plan_service.get_plan(data.plan_id):
            raise not_found("plan")

        if self.customer_service.get_active_membership(db_customer.memberships):
            raise confict("user already has a membership")


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
