from app.database import Session, SessionDep
from sqlmodel import select
from app.models.customers import Customer
from app.utilities.exceptions import not_found, invalid
from fastapi import Depends
from typing import Annotated

from app.schemes.customer import CustomerCreate, CustomerUpdate, CustomerPublic


class CustomerService:
    def __init__(self, session: Session):
        self.session = session

    def find_customer(self, nuip: int) -> Customer | None:
        statement = select(Customer).where(Customer.nuip == nuip)
        return self.session.exec(statement).first()

    def create_customer(self, customer: CustomerCreate) -> CustomerPublic:

        db_customer = self.find_customer(customer.nuip)

        if db_customer:
            raise invalid("customer")

        db_customer = Customer.model_validate(customer)

        self.session.add(db_customer)
        self.session.commit()
        self.session.refresh(db_customer)

        return db_customer

    def read_customers(self) -> list[CustomerPublic]:
        statement = select(Customer)
        return self.session.exec(statement).all()

    # update

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


def get_customer_Service(session: SessionDep) -> CustomerService:
    return CustomerService(
        session=session
    )


CustomerServiceDep = Annotated[CustomerService, Depends(get_customer_Service)]
