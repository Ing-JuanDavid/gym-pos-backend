"""
app/services/customer.py  (reemplaza el archivo completo)

Cambios respecto a tu versión:
- La consulta "con membresía, última asistencia y foto" vive en UN solo lugar
  (_public_query) y la usan read_customers, read_customer y read_customer_by_nuip.
- Se añade photo_url (foto más reciente del cliente).
- create_customer y update_customer devuelven el CustomerPublic COMPLETO. Antes
  devolvían el modelo de BD, así que membership_name, last_attendance (y ahora
  photo_url) llegaban en null y el front los perdía al editar un cliente.
- get_latest_photo_url(): para el evento de acceso en tiempo real.
"""
from typing import Annotated

from fastapi import Depends
from sqlalchemy import func
from sqlmodel import desc, select

from app.database import Session, SessionDep
from app.models.attendance import Attendance
# <-- ajusta la ruta de tu modelo
from app.models.customer_photo import CustomerPhoto
from app.models.customers import Customer
from app.models.membership import Membership
from app.models.plan import Plan
from app.schemes.customer import CustomerCreate, CustomerPublic, CustomerUpdate
from app.utilities.exceptions import invalid, not_found


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

        return self.read_customer(db_customer.customer_id)

    # ── lecturas ──

    def _public_query(self):
        """Cliente + membresía activa + última asistencia + foto más reciente."""

        last_attendance = (
            select(
                Attendance.customer_id,
                func.max(Attendance.check_in).label("last_attendance"),
            )
            .group_by(Attendance.customer_id)
            .subquery()
        )

        # La foto más reciente es la de id más alto de cada cliente.
        newest_photo = (
            select(
                CustomerPhoto.customer_id,
                func.max(CustomerPhoto.id).label("photo_id"),
            )
            .group_by(CustomerPhoto.customer_id)
            .subquery()
        )

        latest_photo = (
            select(CustomerPhoto.customer_id, CustomerPhoto.url)
            .join(newest_photo, CustomerPhoto.id == newest_photo.c.photo_id)
            .subquery()
        )

        return (
            select(
                Customer,
                Plan.name.label("membership_name"),
                last_attendance.c.last_attendance,
                latest_photo.c.url.label("photo_url"),
            )
            .outerjoin(
                Membership,
                (Membership.customer_id == Customer.customer_id)
                & (Membership.status == True)  # noqa: E712
            )
            .outerjoin(Plan, Plan.plan_id == Membership.plan_id)
            .outerjoin(
                last_attendance,
                last_attendance.c.customer_id == Customer.customer_id,
            )
            .outerjoin(
                latest_photo,
                latest_photo.c.customer_id == Customer.customer_id,
            )
        )

    @staticmethod
    def _to_public(row) -> CustomerPublic:
        customer, membership_name, last_attendance, photo_url = row

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
            photo_url=photo_url,
        )

    def read_customers(self) -> list[CustomerPublic]:
        rows = self.session.exec(self._public_query()).all()
        return [self._to_public(row) for row in rows]

    def read_customer(self, customer_id: int) -> CustomerPublic | None:
        query = self._public_query().where(Customer.customer_id == customer_id)
        row = self.session.exec(query).first()
        return self._to_public(row) if row else None

    def read_customer_by_nuip(self, nuip: int) -> CustomerPublic | None:
        query = self._public_query().where(Customer.nuip == nuip)
        row = self.session.exec(query).first()
        return self._to_public(row) if row else None

    def get_latest_photo_url(self, customer_id: int) -> str | None:
        """URL relativa ('/media/captures/...') de la foto más reciente, o None."""
        statement = (
            select(CustomerPhoto.url)
            .where(CustomerPhoto.customer_id == customer_id)
            .order_by(desc(CustomerPhoto.id))
            .limit(1)
        )
        return self.session.exec(statement).first()

    # ── update ──

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

        return self.read_customer(db_customer.customer_id)

    # ── delete ──

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
