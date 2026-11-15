import asyncio
import json

from app.services.device_connection_manager import manager
from app.schemes.device import DeviceCommand
from app.utilities.exceptions import conflict

from collections import defaultdict, deque
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Request, WebSocket, WebSocketDisconnect
from app.services.customer import CustomerServiceDep
from app.services.fingerprint import FingerPrintServiceDep, FingerPrintService
from app.utilities.exceptions import not_found
from app.schemes.fingerprint import FingerPrintCreate
from app.services.attendance import AttendanceServiceDep, AttendanceService, AttendanceResult
from app.services.customer_photo import CustomerPhotoServiceDep      # <-- ajustar ruta
from app.schemes.customer_photo import CustomerPhotoCreate           # <-- ajustar ruta
from app.schemes.devices import EnrollFingerprintRequest, AttendanceRequest, CaptureRequest

router = APIRouter(prefix="/devices", tags=["Devices"])

# Prototipo: cola temporal en memoria por dispositivo.
commands = defaultdict(deque)

# Segundos que se espera la respuesta del ESP32 al eliminar una huella.
DELETE_TIMEOUT = 10
ENROLL_TIMEOUT = 15

# Captura de fotos con el ESP32-CAM
CAPTURE_TIMEOUT = 15                       # segundos esperando la imagen
MAX_IMAGE_BYTES = 5 * 1024 * 1024          # 5 MB de seguridad
# carpeta donde se guardan los archivos
CAPTURES_DIR = Path("media/captures")
# prefijo de la URL que se guarda en la BD
CAPTURES_URL = "/media/captures"


pending_enrollments: dict[int, asyncio.Future] = {}

# print_id -> Future que se resuelve cuando el ESP32 responde
# DELETE_SUCCESS o DELETE_FAILED.
pending_deletions: dict[int, asyncio.Future] = {}

# device_id -> Future que se resuelve cuando el ESP32-CAM envía la imagen
# (o informa un fallo). Solo se permite una captura a la vez por dispositivo.
pending_captures: dict[str, asyncio.Future] = {}


@router.websocket("/ws/{device_id}")
async def device_websocket(
    websocket: WebSocket,
    device_id: str,
    fingerprint_service: FingerPrintServiceDep,
    attendance_service:  AttendanceServiceDep
):
    await manager.connect(
        device_id,
        websocket,
    )

    try:

        while True:

            message = await websocket.receive_json()

            print(
                f"[WS] {device_id} -> {message}"
            )

            event_type = message.get("type")

            match event_type:
                case "ENROLL_SUCCESS":
                    _resolve_enrollment(
                        message["fingerprint_id"],
                        ok=True,
                        reason=None
                    )
                case "FINGER_DETECTED":
                    await handle_finger_detected(message, websocket, fingerprint_service, attendance_service)

                case "DELETE_SUCCESS":
                    _resolve_deletion(
                        message["fingerprint_id"],
                        ok=True,
                        reason=None,
                    )

                case "ENROLL_FAILED":

                    fingerprint_id = message[
                        "fingerprint_id"
                    ]

                    pending_enrollments.pop(
                        fingerprint_id,
                        None,
                    )
                case "FINGER_NOT_FOUND":
                    await websocket.send_json({"type": DeviceCommand.DENY_ACCESS})

                case "DELETE_FAILED":
                    _resolve_deletion(
                        message["fingerprint_id"],
                        ok=False,
                        reason=message.get("status"),
                    )

    except WebSocketDisconnect:

        manager.disconnect(
            device_id,
            websocket,
        )


@router.websocket("/ws/cam/{device_id}")
async def camera_websocket(websocket: WebSocket, device_id: str):
    """
    WebSocket del ESP32-CAM (órdenes y eventos, en JSON).
    La imagen NO viaja por aquí: el ESP32-CAM la sube por HTTP a
    POST /devices/captures/upload/{device_id}.
    """
    await manager.connect(device_id, websocket)

    try:
        while True:
            message = await websocket.receive()

            if message["type"] == "websocket.disconnect":
                break

            if message.get("text") is not None:
                try:
                    data = json.loads(message["text"])
                except json.JSONDecodeError:
                    continue

                print(f"[WS-CAM] {device_id} -> {data}")

                if data.get("type") == "CAPTURE_FAILED":
                    _resolve_capture(device_id, error=data.get("status"))

    finally:
        manager.disconnect(device_id, websocket)


@router.post("/fingerprints/enroll")
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

    result = await _enroll_on_device(request.device_id,  print_id)

    if not result["ok"]:
        raise conflict("el dispositivo no pudo registrar la huella")

    fingerprint_service.create_fingerprint(
        FingerPrintCreate(print_id=print_id,
                          customer_id=db_customer.customer_id)
    )

    return {
        "message": "Huella registrada",
        "customer_nuip": db_customer.nuip,
        "fingerprint_id": print_id,
    }


@router.delete("/fingerprints/{customer_nuip}")
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

    result = await _delete_on_device(device_id, print_id)

    if not result["ok"]:
        raise HTTPException(
            status_code=502,
            detail=(
                f"El dispositivo no pudo eliminar la huella {print_id}: "
                f"{result['reason']}"
            ),
        )

    # El sensor confirmó: ahora sí se elimina de la base de datos.
    fingerprint_service.delete_fingerprint(db_fingerprint)

    return {
        "message": "Huella eliminada",
        "customer_nuip": customer_nuip,
        "fingerprint_id": print_id,
    }


@router.post("/captures/upload/{device_id}")
async def upload_capture(device_id: str, request: Request):
    """
    Lo llama el ESP32-CAM con el JPEG como cuerpo de la petición.
    Solo se acepta si hay una captura pendiente para ese dispositivo.
    """
    if device_id not in pending_captures:
        raise HTTPException(
            status_code=409,
            detail="No hay una captura pendiente para este dispositivo",
        )

    image = await request.body()

    if len(image) > MAX_IMAGE_BYTES:
        raise HTTPException(status_code=413, detail="Imagen demasiado grande")

    print(f"[CAM-UPLOAD] {device_id} -> {len(image)} bytes")

    _resolve_capture(device_id, image=image)

    return {"message": "Imagen recibida", "size": len(image)}


@router.post("/captures")
async def capture_customer_photo(
    request: CaptureRequest,
    customer_service: CustomerServiceDep,
    photo_service: CustomerPhotoServiceDep,
):
    db_customer = customer_service.get_customer(request.customer_nuip)

    if not db_customer:
        raise not_found("customer")

    result = await _capture_on_device(request.device_id)

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


# @router.post("/attendance/start")
# async def start_attendance(
#     request: AttendanceRequest,
# ):
#     sent = await manager.send_command(
#         device_id=request.device_id,
#         command={
#             "type": "VERIFY",
#         },
#     )

#     if not sent:
#         raise conflict("dispositivo desconectado")

#     return {
#         "message": "Proceso de validación iniciado"
#     }


async def _enroll_on_device(device_id: str, print_id: int):
    if print_id in pending_enrollments:
        raise conflict(
            f"ya hay un registro en curso para la huella {print_id}")

    future = asyncio.get_running_loop().create_future()
    pending_enrollments[print_id] = future

    try:
        command = {
            "type": DeviceCommand.ENROLL,
            "fingerprint_id": print_id,
        }

        await send_device_command(device_id, command)

        try:
            return await asyncio.wait_for(future, timeout=ENROLL_TIMEOUT)
        except asyncio.TimeoutError:
            raise conflict("el dispositivo no respondio a tiempo")

    finally:
        pending_enrollments.pop(print_id, None)


async def _delete_on_device(device_id: str, print_id: int) -> dict:
    if print_id in pending_deletions:
        raise conflict(
            "ya hay una eliminación en curso para la huella {print_id}")
    future = asyncio.get_running_loop().create_future()
    pending_deletions[print_id] = future

    try:
        command = {
            "type": DeviceCommand.DELETE_FINGERPRINT,
            "fingerprint_id": print_id,
        }

        await send_device_command(device_id, command)

        try:
            return await asyncio.wait_for(future, timeout=DELETE_TIMEOUT)
        except asyncio.TimeoutError:
            raise conflict("el dispositivo no respondio a tiempo")

    finally:
        pending_deletions.pop(print_id, None)


async def _capture_on_device(device_id: str) -> dict:
    """
    Envía CAPTURE al ESP32-CAM y espera la imagen.
    Devuelve {"ok": True, "image": bytes} o {"ok": False, "reason": str}.
    Lanza HTTPException si no está conectado o no responde.
    """
    if device_id in pending_captures:
        raise HTTPException(
            status_code=409,
            detail="Ya hay una captura en curso en este dispositivo",
        )

    future = asyncio.get_running_loop().create_future()
    pending_captures[device_id] = future

    try:
        sent = await manager.send_command(
            device_id=device_id,
            command={"type": "CAPTURE"},
        )

        if not sent:
            raise HTTPException(
                status_code=409,
                detail="Dispositivo desconectado",
            )

        try:
            return await asyncio.wait_for(future, timeout=CAPTURE_TIMEOUT)
        except asyncio.TimeoutError:
            raise HTTPException(
                status_code=504,
                detail="La cámara no respondió a tiempo",
            )

    finally:
        pending_captures.pop(device_id, None)


def _resolve_deletion(fingerprint_id: int, ok: bool, reason: str | None):
    """Despierta al endpoint que espera la respuesta del ESP32."""
    future = pending_deletions.get(fingerprint_id)

    if future is not None and not future.done():
        future.set_result({"ok": ok, "reason": reason})


def _resolve_enrollment(fingerprint_id: int, ok: bool, reason: str | None):
    """Despierta al endpoint que espera la respuesta del ESP32."""
    future = pending_enrollments.get(fingerprint_id)

    if future is not None and not future.done():
        future.set_result({"ok": ok, "reason": reason})


def _resolve_capture(
    device_id: str,
    image: bytes | None = None,
    error: str | None = None,
):
    """Despierta al endpoint que espera la foto del ESP32-CAM."""
    future = pending_captures.get(device_id)

    if future is None or future.done():
        return

    if image is not None:
        future.set_result({"ok": True, "image": image})
    else:
        future.set_result({"ok": False, "reason": error or "UNKNOWN"})


async def handle_finger_detected(message: dict, websocket: WebSocket, fingerprint_service: FingerPrintService, attendance_service: AttendanceService):
    fingerprint_id = message["fingerprint_id"]

    db_fingerprint = (
        fingerprint_service.get_fingerprint_by_print_id(
            fingerprint_id
        )
    )

    if db_fingerprint is None:
        print(
            f"Fingerprint {fingerprint_id} no existe"
        )

        # Responder para que el ESP32 no espere el timeout de 5 s.
        await websocket.send_json({"type": DeviceCommand.DENY_ACCESS})
        return

    response = attendance_service.register_attendance(
        db_fingerprint.customer.nuip
    )

    command = (
        DeviceCommand.ALLOW_ACCESS
        if response.status in (AttendanceResult.CHECK_OUT, AttendanceResult.CHECK_IN)
        else DeviceCommand.DENY_ACCESS
    )
    print(
        f"Attendance status={response.status.value} "
        f"Sending command={command.value} "
        f"for fingerprint={fingerprint_id}"
    )
    await websocket.send_json({"type": command})


async def send_device_command(
    device_id: str,
    command: dict,
):

    print("sending....")

    sent = await manager.send_command(
        device_id=device_id,
        command=command,
    )

    if not sent:
        raise HTTPException(
            status_code=409,
            detail="Dispositivo desconectado",
        )
