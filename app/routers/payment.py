from fastapi import APIRouter
from app.models.payment import Payment, PaymentDetail
from app.schemes.payment import PaymentCreate
from app.services.payment import PaymentServiceDep

router = APIRouter(prefix="/payments", tags=["payments"])


@router.post("/{customer_id}", response_model=Payment)
async def create_payment(customer_id: int, payment: PaymentCreate, service: PaymentServiceDep):
    return service.create_payment(customer_id, payment)


@router.get("/customer/{customer_id}", response_model=list[Payment])
def get_payments_by_customer_endpoint(
    customer_id: int,
    service: PaymentServiceDep
):
    return service.get_payments_by_customer(customer_id)


@router.get("/{payment_id}/details", response_model=list[PaymentDetail])
def get_payment_details_endpoint(
    payment_id: int,
    service: PaymentServiceDep
):
    return service.get_payment_details(payment_id)
