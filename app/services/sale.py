from app.database import Session, SessionDep
from sqlmodel import select
from fastapi import HTTPException, Depends
from datetime import datetime

from app.models.product import Product
from app.models.sale import Sale, SaleDetail
from app.models import Plan
from app.models.customers import Customer
from app.schemes.sale import SaleCreate, SaleResume
from app.utilities.exceptions import not_found, conflict
from typing import Annotated
from app.services.membership import MembershipService
from app.services.customer import CustomerService, CustomerServiceDep


class SaleService:
    def __init__(self, session: Session, customer_service: CustomerService):
        self.session = session
        self.customer_service = customer_service

    def get_sale(self, sale_id: int) -> Sale:
        db_sale = self.session.get(Sale, sale_id)

        if not db_sale:
            raise not_found("sale")

        return db_sale

    def create_sale(self, sale: SaleCreate) -> Sale:

        db_customer = self.customer_service.get_customer(sale.nuip)

        if not db_customer:
            raise not_found("customer")

        total_amount = 0
        sale_details = []

        for d in sale.details:
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
                membership = self.customer_service.get_active_membership(
                    db_customer.memberships)

                if membership:
                    raise conflict("customer already has a membership")

                plan = self.session.get(Plan, d.item_id)
                if not plan:
                    raise not_found("plan")

                unit_price = plan.amount
                total_amount += unit_price

            else:
                raise conflict("invalid type item")

            sale_details.append(
                SaleDetail(
                    item_type=d.item_type,
                    item_id=d.item_id,
                    quantity=d.quantity,
                    unit_price=unit_price
                )
            )

        # crear cabecera
        sale = Sale(
            customer_id=db_customer.customer_id,
            nuip=db_customer.nuip,
            total=total_amount,
            details=sale_details
        )
        self.session.add(sale)
        self.session.commit()
        self.session.refresh(sale)

        return sale

    def get_sales_by_customer(self, customer_id: int) -> list[Sale]:
        """Obtiene todos las ventas de un cliente."""
        statement = select(Sale).where(Sale.customer_id == customer_id)
        return self.session.exec(statement).all()

    def get_sale_resume(self, sale_id: int) -> SaleResume:
        """Obtiene el detalle de una venta específica."""
        db_sale = self.get_sale(sale_id)

        return SaleResume(
            sale_id=db_sale.sale_id,
            nuip=db_sale.nuip,
            total=db_sale.total,
            status=db_sale.status,
            created_at=db_sale.created_at,
            pending_amout=self.get_pending_amount(db_sale),
            details=db_sale.details
        )

    def get_pending_amount(self, sale: Sale) -> int:
        return sale.total - sum(p.amount for p in sale.payments)


def get_sale_service(session: SessionDep, customer_service: CustomerServiceDep) -> SaleService:
    return SaleService(session, customer_service)


SaleServiceDep = Annotated[SaleService, Depends(get_sale_service)]


# probar los enpoint de sale
# efecturar logica de descuento de stock y creacion de membresias solo cuanod se realicce el pago de la sale (si el usuario tiene una membresia activa, no puede realizar la compra de un nuevo plan)
# generar lso movimientos respetivos al crar pagos
# crear fingerprit
# proteger endpoinds
