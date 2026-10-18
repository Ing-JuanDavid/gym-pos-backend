from fastapi import APIRouter, Depends, HTTPException
from typing import List
from app.models.payment import Payment
from app.schemes.payment import PaymentCreate
from app.services.payment import PaymentService, PaymentServiceDep

router = APIRouter(prefix="/payments", tags=["payments"])


# Crear un pago
@router.post("/", response_model=Payment)
def create_payment(
    sale_id: int,
    payment: PaymentCreate,
    service: PaymentServiceDep
):
    return service.create_payment(sale_id, payment)


# Obtener todos los pagos de unna venta
@router.get("/sale/{sale_id}", response_model=List[Payment])
def get_payments_by_sale(
    sale_id: int,
    service: PaymentServiceDep
):
    payments = service.get_payments_by_sale(sale_id)
    if not payments:
        raise HTTPException(
            status_code=404, detail="No se encontraron pagos para esta venta")
    return payments
