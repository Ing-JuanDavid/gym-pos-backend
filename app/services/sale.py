from app.database import Session, SessionDep
from sqlmodel import select
from fastapi import HTTPException, Depends
from datetime import datetime

from app.models.product import Product
from app.models.sale import Sale, SaleDetail
from app.models import Plan
from app.models.customers import Customer
from app.schemes.sale import SaleCreate
from app.utilities.exceptions import not_found, conflict
from typing import Annotated


class SaleService:
    def __init__(self, session: Session):
        self.session = session

    def create_sale(self, sale: SaleCreate) -> Sale:

        db_customer = self.session.get(Customer, sale.customer_id)

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
            customer_id=sale.customer_id,
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

    def get_sale_details(self, sale_id: int) -> list[SaleDetail]:
        """Obtiene el detalle de una venta específica."""
        statement = select(SaleDetail).where(
            SaleDetail.sale_id == sale_id)
        return self.session.exec(statement).all()


def get_sale_service(session: SessionDep) -> SaleService:
    return SaleService(session)


SaleServiceDep = Annotated[SaleService, Depends(get_sale_service)]


# probar los enpoint de sale
# efecturar logica de descuento de stock y creacion de membresias solo cuanod se realicce el pago de la sale (si el usuario tiene una membresia activa, no puede realizar la compra de un nuevo plan)
# generar lso movimientos respetivos al crar pagos
# crear fingerprit
# proteger endpoinds
