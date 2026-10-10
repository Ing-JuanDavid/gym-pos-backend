from fastapi import APIRouter, Path
from app.services.customer import CustomerService, CustomerServiceDep
from app.schemes.customer import CustomerPublic, CustomerCreate, CustomerUpdate
from app.utilities.exceptions import not_found

router = APIRouter(prefix="/customers", tags=["customer"])


@router.get("", response_model=list[CustomerPublic])
async def read_all(service: CustomerServiceDep):
    return service.read_customers()


@router.get("/{nuip}", response_model=CustomerPublic)
async def get_customer(nuip: int, service: CustomerServiceDep):
    db_customer = service.get_customer(nuip)

    if not db_customer:
        raise not_found("customer")

    return db_customer


@router.post("", response_model=CustomerPublic)
async def create_customer(service: CustomerServiceDep, customer: CustomerCreate):
    return service.create_customer(customer)


@router.patch("/{nuip}", response_model=CustomerPublic)
async def update_customer(service: CustomerServiceDep, customer: CustomerUpdate, nuip: int = Path(gt=0)):
    return service.update_customer(nuip, customer)


@router.delete("/{nuip}", response_model=dict[str, str])
async def delete_customer(service: CustomerServiceDep, nuip: int = Path(gt=0)):
    service.delete_customer(nuip)
    return {"messaje": "ok"}
