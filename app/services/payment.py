from app.database import Session, SessionDep
from sqlmodel import select
from fastapi import HTTPException, Depends
from datetime import datetime
from typing import Optional

from app.models import Payment
from app.models.sale import Sale
from app.models.customers import Customer
from app.schemes.payment import PaymentCreate
from app.utilities.exceptions import not_found, conflict
from typing import Annotated
from app.services.sale import SaleService, SaleServiceDep
from app.models.sale import SaleStatus, SaleDetail
from app.models.cash_movement import CashMovement, MovementType
from app.models.payment import PaymentMethod
from app.services.cash_movement import CashMovementService, CashMovementServiceDep
from app.services.membership import MembershipService, MembershipServiceDep
from app.schemes.membership import MembershipCreate
from app.services.plan import PlanService, PlanServiceDep
from app.models.plan import Plan

from app.models.product import Product


class PaymentService:
    def __init__(
        self,
        session: Session,
        sale_service: SaleService,
        cash_movement_service: CashMovementService,
        membership_service: MembershipService,
        plan_service: PlanService
    ):
        self.session = session
        self.sale_service = sale_service
        self.cash_movement_service = cash_movement_service
        self.membership_service = membership_service
        self.plan_service = plan_service

    def create_payment(self, sale_id: int, payment: PaymentCreate) -> Payment:
        try:
            db_sale = self.sale_service.get_sale(sale_id)

            if db_sale.status == SaleStatus.PAGADA:
                raise conflict("sale already paid")

            pending_amount = self.sale_service.get_pending_amount(db_sale)

            if payment.amount > pending_amount:
                raise conflict("invald amount")

            # payment
            db_payment = Payment(
                amount=payment.amount,
                payment_method=payment.payment_method,
                sale_id=sale_id
            )

            db_sale.payments.append(db_payment)
            pending_amount -= payment.amount
            db_sale.status = SaleStatus.PAGADA if pending_amount == 0 else SaleStatus.PARCIAL

            if db_sale.status == SaleStatus.PAGADA:
                self.confirm_purchase(db_sale)
            #  create a cash movmeent
            self.cash_movement_service.create_movement(
                db_payment.amount, db_payment.payment_method, MovementType.ENTRADA)

            self.session.commit()
            self.session.refresh(db_payment)

        except Exception as e:
            self.session.rollback()
            raise e
        return db_payment

    def get_payments_by_sale(self, sale_id: int) -> list[Payment]:
        """Obtiene todos los pagos de una venta."""
        statement = select(Payment).where(Payment.sale_id == sale_id)
        return self.session.exec(statement).all()

    def get_plan_from_details(self, details: list[SaleDetail]) -> Optional[Plan]:
        for d in details:
            if d.item_type == "PLAN":
                return self.plan_service.get_plan(d.item_id)

        return None

    def confirm_purchase(self, sale: Sale):
        for d in sale.details:
            if d.item_type == "PRODUCT":
                db_product = self.session.get(Product, d.item_id)

                if not db_product:
                    raise not_found("product")

                db_product.stock -= d.quantity

            elif d.item_type == "PLAN":
                db_plan = self.plan_service.get_plan(d.item_id)
                db_membership = self.membership_service.create_membership(
                    MembershipCreate(
                        customer_id=sale.customer_id,
                        plan_id=db_plan.plan_id,
                    )
                )


def get_payment_service(session: SessionDep, sale_service: SaleServiceDep, cash_movement_service: CashMovementServiceDep, membership_service: MembershipServiceDep, plan_service: PlanServiceDep) -> PaymentService:
    return PaymentService(session, sale_service, cash_movement_service, membership_service, plan_service)


PaymentServiceDep = Annotated[PaymentService, Depends(get_payment_service)]
