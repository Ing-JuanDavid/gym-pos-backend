from app.database import Session, SessionDep
from sqlmodel import select
from fastapi import HTTPException, Depends
from datetime import datetime

from app.models import Payment, PaymentDetail, Product
from app.models import Plan
from app.models.customers import Customer
from app.schemes.payment import PaymentCreate
from app.utilities.exceptions import not_found, conflict
from typing import Annotated


class PaymentService:
    def __init__(self, session: Session):
        self.session = session

    def create_payment(self, customer_id: int, payment: PaymentCreate) -> Payment:

        db_customer = self.session.get(Customer, customer_id)

        if not db_customer:
            raise not_found("customer")

        total_amount = 0
        payment_details = []

        for d in payment.details:
            if d.item_type == "PRODUCTO":
                product = self.session.get(Product, d.item_id)
                if not product:
                    raise not_found("product")
                if product.stock < d.quantity:
                    raise conflict("insufficient stock")

                # usar precio real del producto
                unit_price = product.price
                total_amount += d.quantity * unit_price

                # disminuir stock
                product.stock -= d.quantity
                self.session.add(product)

            elif d.item_type == "PLAN":
                # aquí deberías obtener la membresía desde la BD
                # por ejemplo: membership = self.session.get(Membership, d["item_id"])
                # unit_price = membership.plan.amount
                # para simplificar, supongamos que membership tiene un campo "price"
                plan = self.session.get(Plan, d.item_id)
                if not plan:
                    raise not_found("plan")

                unit_price = plan.amount
                total_amount += unit_price

            else:
                raise conflict("invalid type item")

            payment_details.append(
                PaymentDetail(
                    item_type=d.item_type,
                    item_id=d.item_id,
                    quantity=d.quantity,
                    unit_price=unit_price
                )
            )

        # crear cabecera
        payment = Payment(
            customer_id=customer_id,
            amount=total_amount,
            payment_method=payment.payment_method,
        )
        self.session.add(payment)
        self.session.commit()
        self.session.refresh(payment)

        # guardar detalles
        for detail in payment_details:
            detail.payment_id = payment.payment_id
            self.session.add(detail)

        self.session.commit()
        self.session.refresh(payment)
        return payment

    def get_payments_by_customer(self, customer_id: int) -> list[Payment]:
        """Obtiene todos los pagos de un cliente."""
        statement = select(Payment).where(Payment.customer_id == customer_id)
        return self.session.exec(statement).all()

    def get_payment_details(self, payment_id: int) -> list[PaymentDetail]:
        """Obtiene el detalle de un pago específico."""
        statement = select(PaymentDetail).where(
            PaymentDetail.payment_id == payment_id)
        return self.session.exec(statement).all()


def get_payment_service(session: SessionDep) -> PaymentService:
    return PaymentService(session)


PaymentServiceDep = Annotated[PaymentService, Depends(get_payment_service)]


# pulir los dto de payment .
# crear cash movement crud
# cuando una memebrsia sea asignada, generar un payment y un moviiento de caja asociado
# al egnerar una asistencia si es por membersia diaria, generar un movimiento de pago
# busccar un mecanismo para
# crear fingerprit
# proteger endpoinds
