from fastapi import APIRouter
from app.models.sale import Sale, SaleDetail
from app.schemes.sale import SaleCreate, SaleResume
from app.services.sale import SaleServiceDep

router = APIRouter(prefix="/sales", tags=["sales"])


@router.get("", response_model=list[Sale])
async def get_sales(service: SaleServiceDep):
    return service.list_sales()


@router.post("", response_model=Sale)
async def create_sale(sale: SaleCreate, service: SaleServiceDep):
    return service.create_sale(sale)


@router.get("/customer/{nuip}", response_model=list[Sale])
def get_sales_by_customer(
    nuip: int,
    service: SaleServiceDep
):
    return service.get_sales_by_customer(nuip)


@router.get("/{sale_id}/resume", response_model=SaleResume)
def get_sale_resume(
    sale_id: int,
    service: SaleServiceDep
):
    return service.get_sale_resume(sale_id)


@router.get("/{sale_id}", response_model=Sale)
def get_sale(
    sale_id: int,
    service: SaleServiceDep
):
    return service.get_sale(sale_id)


@router.delete("/{sale_id}", response_model=dict[str, str])
def delete_sale(
    sale_id: int,
    service: SaleServiceDep
):

    if not service.delete_sale(sale_id):
        return {"message": "error"}
    return {"message": "ok"}
