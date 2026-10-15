from fastapi import APIRouter
from app.models.sale import Sale, SaleDetail
from app.schemes.sale import SaleCreate
from app.services.sale import SaleServiceDep

router = APIRouter(prefix="/sales", tags=["sales"])


@router.post("", response_model=Sale)
async def create_sale(sale: SaleCreate, service: SaleServiceDep):
    return service.create_sale(sale)


@router.get("/customer/{customer_id}", response_model=list[Sale])
def get_payments_by_customer_endpoint(
    customer_id: int,
    service: SaleServiceDep
):
    return service.get_sales_by_customer(customer_id)


@router.get("/{sale_id}/details", response_model=list[SaleDetail])
def get_payment_details_endpoint(
    sale_id: int,
    service: SaleServiceDep
):
    return service.get_sale_details(sale_id)
