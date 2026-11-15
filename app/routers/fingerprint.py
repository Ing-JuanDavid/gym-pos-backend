from fastapi import APIRouter
from app.schemes.devices import EnrollFingerprintRequest, DeviceCommand
from app.schemes.fingerprint import FingerPrintCreate
from app.services.customer import CustomerServiceDep
from app.services.fingerprint import FingerPrintServiceDep
from app.utilities.exceptions import not_found, conflict
from app.helpers import device_helpers
from app.services.device_connection_manager import manager


router = APIRouter(prefix="/fingerprint", tags=["fingerprint"])


@router.post("")
async def enroll_fingerprint(
    request: EnrollFingerprintRequest,
    customer_service: CustomerServiceDep,
    fingerprint_service: FingerPrintServiceDep
):

    db_customer = customer_service.get_customer(request.customer_nuip)

    if not db_customer:
        raise not_found("customer")

    if fingerprint_service.get_fingerprint(db_customer.customer_id):
        raise conflict("customer's print already enrolled")

    print_id = fingerprint_service.get_fingerprint_id()

    result = await device_helpers._enroll_on_device(request.device_id,  print_id)

    if not result["ok"]:
        raise conflict(
            f"el dispositivo no pudo registrar la huella {print_id}")

    fingerprint_service.create_fingerprint(
        FingerPrintCreate(print_id=print_id,
                          customer_id=db_customer.customer_id)
    )

    return {
        "message": "Huella registrada",
        "customer_nuip": db_customer.nuip,
        "fingerprint_id": print_id,
    }


@router.delete("/{customer_nuip}")
async def delete_fingerprint(
    customer_nuip: int,
    customer_service: CustomerServiceDep,
    fingerprint_service: FingerPrintServiceDep,
    device_id: str = "esp-32",
):
    db_customer = customer_service.get_customer(customer_nuip)

    if not db_customer:
        raise not_found("customer")

    db_fingerprint = fingerprint_service.get_fingerprint(
        db_customer.customer_id
    )

    if not db_fingerprint:
        raise not_found("fingerprint")

    print_id = db_fingerprint.print_id

    result = await device_helpers._delete_on_device(device_id, print_id)

    if not result["ok"]:
        raise conflict(
            f"el dispositivo no puedo eliminar la huella {print_id}")

    # El sensor confirmó: ahora sí se elimina de la base de datos.
    fingerprint_service.delete_fingerprint(db_fingerprint)

    return {
        "message": "Huella eliminada",
        "customer_nuip": customer_nuip,
        "fingerprint_id": print_id,
    }
