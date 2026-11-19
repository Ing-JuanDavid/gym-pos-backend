import asyncio
from app.services.device_connection_manager import manager
from app.services.attendance import AttendanceServiceDep, AttendanceService, AttendanceResult
from app.services.fingerprint import FingerPrintService
from app.schemes.devices import DeviceCommand
from app.utilities.exceptions import conflict
from fastapi import WebSocket, HTTPException
from app.services.frontend_hub import hub, access_event


DELETE_TIMEOUT = 10
ENROLL_TIMEOUT = 45
pending_enrollments: dict[int, asyncio.Future] = {}

# print_id -> Future que se resuelve cuando el ESP32 responde
# DELETE_SUCCESS o DELETE_FAILED.
pending_deletions: dict[int, asyncio.Future] = {}


# device_id -> Future que se resuelve cuando el ESP32-CAM envía la imagen
# (o informa un fallo). Solo se permite una captura a la vez por dispositivo.
pending_captures: dict[str, asyncio.Future] = {}
CAPTURE_TIMEOUT = 15                       # segundos esperando la imagen


# helpers for finerprint sensor

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

        await manager.send_device_command(device_id, command)

        try:
            return await asyncio.wait_for(future, timeout=ENROLL_TIMEOUT)
        except asyncio.TimeoutError:
            raise conflict("el dispositivo no respondio a tiempo")

    finally:
        pending_enrollments.pop(print_id, None)


async def _delete_on_device(device_id: str, print_id: int) -> dict:
    if print_id in pending_deletions:
        raise conflict(
            f"ya hay una eliminación en curso para la huella {print_id}")
    future = asyncio.get_running_loop().create_future()
    pending_deletions[print_id] = future

    try:
        command = {
            "type": DeviceCommand.DELETE_FINGERPRINT,
            "fingerprint_id": print_id,
        }

        await manager.send_device_command(device_id, command)

        try:
            return await asyncio.wait_for(future, timeout=DELETE_TIMEOUT)
        except asyncio.TimeoutError:
            raise conflict("el dispositivo no respondio a tiempo")

    finally:
        pending_deletions.pop(print_id, None)


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


async def handle_finger_detected(message, websocket, fingerprint_service,
                                 attendance_service, device_id: str):
    fingerprint_id = message["fingerprint_id"]
    db_fingerprint = fingerprint_service.get_fingerprint_by_print_id(
        fingerprint_id)

    if db_fingerprint is None:
        await websocket.send_json({"type": DeviceCommand.DENY_ACCESS})
        await hub.broadcast(access_event(
            device_id=device_id, granted=False, reason="FINGER_NOT_FOUND"))
        return

    customer = db_fingerprint.customer
    response = attendance_service.register_attendance(customer.nuip)
    granted = response.status in (
        AttendanceResult.CHECK_OUT, AttendanceResult.CHECK_IN)

    # 1) El ESP primero (espera respuesta en menos de 5 s).
    await websocket.send_json({
        "type": DeviceCommand.ALLOW_ACCESS if granted else DeviceCommand.DENY_ACCESS})

    # 2) Después la UI. hub.broadcast nunca lanza excepciones.
    await hub.broadcast(access_event(
        device_id=device_id,
        granted=granted,
        access_type=response.status.value if granted else None,
        reason=None if granted else response.status.value,
        customer={
            "nuip": customer.nuip,
            "full_name": f"{customer.first_name} {customer.last_name}",
            "photo_url": None,       # TODO: URL de la foto más reciente del cliente
        },
        membership_end=None,         # TODO: fecha fin de la membresía activa
    ))
# helpers for esp-cam


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
