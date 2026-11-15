from fastapi import APIRouter, Request, HTTPException
from app.utilities.exceptions import not_found
from pathlib import Path
from app.helpers import device_helpers
from app.schemes.devices import CaptureRequest
from datetime import datetime
from uuid import uuid4

from app.services.customer import CustomerServiceDep
from app.services.customer_photo import CustomerPhotoServiceDep      # <-- ajustar ruta
from app.schemes.customer_photo import CustomerPhotoCreate

import asyncio


router = APIRouter(prefix="/capture", tags=["photo"])


# Captura de fotos con el ESP32-CAM

MAX_IMAGE_BYTES = 5 * 1024 * 1024          # 5 MB de seguridad
# carpeta donde se guardan los archivos
CAPTURES_DIR = Path("media/captures")
# prefijo de la URL que se guarda en la BD
CAPTURES_URL = "/media/captures"


@router.post("/upload/{device_id}")
async def upload_capture(device_id: str, request: Request):
    """
    Lo llama el ESP32-CAM con el JPEG como cuerpo de la petición.
    Solo se acepta si hay una captura pendiente para ese dispositivo.
    """
    if device_id not in device_helpers.pending_captures:
        raise HTTPException(
            status_code=409,
            detail="No hay una captura pendiente para este dispositivo",
        )

    image = await request.body()

    if len(image) > MAX_IMAGE_BYTES:
        raise HTTPException(status_code=413, detail="Imagen demasiado grande")

    print(f"[CAM-UPLOAD] {device_id} -> {len(image)} bytes")

    device_helpers._resolve_capture(device_id, image=image)

    return {"message": "Imagen recibida", "size": len(image)}


@router.post("")
async def capture_customer_photo(
    request: CaptureRequest,
    customer_service: CustomerServiceDep,
    photo_service: CustomerPhotoServiceDep,
):
    db_customer = customer_service.get_customer(request.customer_nuip)

    if not db_customer:
        raise not_found("customer")

    result = await device_helpers._capture_on_device(request.device_id)

    if not result["ok"]:
        raise HTTPException(
            status_code=502,
            detail=f"La cámara no pudo capturar la imagen: {result['reason']}",
        )

    image: bytes = result["image"]

    # Validaciones básicas: tamaño y cabecera JPEG (FF D8)
    if len(image) > MAX_IMAGE_BYTES or image[:2] != b"\xff\xd8":
        raise HTTPException(
            status_code=502,
            detail="La imagen recibida no es un JPEG válido",
        )

    # 1) Guardar el archivo en la carpeta
    CAPTURES_DIR.mkdir(parents=True, exist_ok=True)

    filename = (
        f"customer_{db_customer.customer_id}_"
        f"{datetime.now():%Y%m%d_%H%M%S}_{uuid4().hex[:8]}.jpg"
    )
    file_path = CAPTURES_DIR / filename

    await asyncio.to_thread(file_path.write_bytes, image)

    # 2) Guardar solo la URL en la base de datos
    url = f"{CAPTURES_URL}/{filename}"

    try:
        db_photo = photo_service.create_photo(
            CustomerPhotoCreate(
                url=url,
                customer_id=db_customer.customer_id,
            )
        )
    except Exception:
        # Si falla la BD, no dejar el archivo huérfano
        file_path.unlink(missing_ok=True)
        raise

    return {
        "message": "Foto capturada",
        "customer_nuip": request.customer_nuip,
        "photo_id": db_photo.id,
        "url": url,
    }
