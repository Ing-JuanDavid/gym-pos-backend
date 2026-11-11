from app.services.customer import CustomerService
import asyncio

from collections import defaultdict, deque
from typing import Literal

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from app.services.customer import CustomerServiceDep
from app.services.fingerprint import FingerPrintServiceDep
from app.utilities.exceptions import not_found
from app.schemes.fingerprint import FingerPrintCreate
from app.services.attendance import AttendanceServiceDep, AttendanceResult

router = APIRouter(prefix="/devices", tags=["Devices"])

# Prototipo: cola temporal en memoria por dispositivo.
commands = defaultdict(deque)

# Segundos que se espera la respuesta del ESP32 al eliminar una huella.
DELETE_TIMEOUT = 10


class CommandCreate(BaseModel):
    device_id: str
    action: Literal["LED_ON", "LED_OFF"]


class EnrollFingerprintRequest(BaseModel):
    device_id: str = "esp-32"
    customer_nuip: int


class AttendanceRequest(BaseModel):
    device_id: str = "esp-32"


pending_enrollments: dict[int, dict] = {}

# print_id -> Future que se resuelve cuando el ESP32 responde
# DELETE_SUCCESS o DELETE_FAILED.
pending_deletions: dict[int, asyncio.Future] = {}


# first realtime comunication method by using only http


# @router.post("/commands")
# def create_command(command: CommandCreate):
#     commands[command.device_id].append(command.action)

#     return {
#         "message": "Orden agregada",
#         "device_id": command.device_id,
#         "action": command.action,
#     }


# @router.get("/commands/next")
# def get_next_command(device_id: str):
#     queue = commands[device_id]

#     if not queue:
#         return {"action": None}

#     return {"action": queue.popleft()}


# second realtime comunication method by using only websockets

# connection manager

class DeviceConnectionManager:
    def __init__(self):
        self.active_devices: dict[str, WebSocket] = {}
        self.send_locks: dict[str, asyncio.Lock] = {}

    async def connect(self, device_id: str, websocket: WebSocket):
        await websocket.accept()
        self.active_devices[device_id] = websocket
        self.send_locks.setdefault(device_id, asyncio.Lock())

    def disconnect(self, device_id: str, websocket: WebSocket):
        # No eliminar una conexión nueva si una antigua acaba de cerrarse.
        if self.active_devices.get(device_id) is websocket:
            self.active_devices.pop(device_id, None)

    async def send_command(self, device_id: str, command: dict) -> bool:
        websocket = self.active_devices.get(device_id)

        if websocket is None:
            return False

        lock = self.send_locks.setdefault(device_id, asyncio.Lock())

        try:
            async with lock:
                # Verificar nuevamente después de adquirir el bloqueo.
                if self.active_devices.get(device_id) is not websocket:
                    return False

                await websocket.send_json(command)

            return True

        except (RuntimeError, WebSocketDisconnect):
            self.disconnect(device_id, websocket)
            return False


manager = DeviceConnectionManager()


def _resolve_deletion(fingerprint_id: int, ok: bool, reason: str | None):
    """Despierta al endpoint que espera la respuesta del ESP32."""
    future = pending_deletions.get(fingerprint_id)

    if future is not None and not future.done():
        future.set_result({"ok": ok, "reason": reason})


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

            if event_type == "ENROLL_SUCCESS":

                fingerprint_id = message[
                    "fingerprint_id"
                ]

                enrollment = pending_enrollments.get(
                    fingerprint_id
                )

                if enrollment:

                    customer_id = enrollment["customer_id"]

                    print(
                        f"Huella registrada customer={customer_id}"
                    )

                    fingerprint_service.create_fingerprint(
                        FingerPrintCreate(print_id=fingerprint_id, customer_id=customer_id))
                    #
                    # user.fingerprint_id = fingerprint_id
                    # session.commit()

                    pending_enrollments.pop(
                        fingerprint_id,
                        None,
                    )

            elif event_type == "FINGER_DETECTED":

                fingerprint_id = message[
                    "fingerprint_id"
                ]

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
                    await websocket.send_json({"type": "DENY_ACCESS"})

                    continue

                response = attendance_service.register_attendance(
                    db_fingerprint.customer.nuip)

                print(response.status.value)
                if response.status in (
                    AttendanceResult.CHECK_IN,
                    AttendanceResult.CHECK_OUT,
                ):
                    print("send json")
                    await websocket.send_json(
                        {
                            "type": "ALLOW_ACCESS"
                        }
                    )
                else:
                    await websocket.send_json(
                        {
                            "type": "DENY_ACCESS"
                        }
                    )

            elif event_type == "ENROLL_FAILED":

                fingerprint_id = message[
                    "fingerprint_id"
                ]

                pending_enrollments.pop(
                    fingerprint_id,
                    None,
                )
            elif event_type == "FINGER_NOT_FOUND":

                await websocket.send_json({"type": "DENY_ACCESS"})

            elif event_type == "DELETE_SUCCESS":

                _resolve_deletion(
                    message["fingerprint_id"],
                    ok=True,
                    reason=None,
                )

            elif event_type == "DELETE_FAILED":

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


@router.post("/commands")
async def create_command(command: CommandCreate):
    sent = await manager.send_command(
        device_id=command.device_id,
        action=command.action,
    )

    if not sent:
        raise HTTPException(
            status_code=409,
            detail=f"El dispositivo '{command.device_id}' no está conectado.",
        )

    return {
        "message": "Orden enviada al dispositivo",
        "device_id": command.device_id,
        "action": command.action,
    }


@router.post("/fingerprints/enroll")
async def enroll_fingerprint(
    request: EnrollFingerprintRequest,
    customer_service: CustomerServiceDep,
    fingerprint_service: FingerPrintServiceDep
):

    db_customer = customer_service.get_customer(request.customer_nuip)

    if not db_customer:
        raise not_found("customer")

    fingerprint_id = fingerprint_service.get_fingerprint_id()

    pending_enrollments[fingerprint_id] = {
        "customer_id": db_customer.customer_id,
    }

    sent = await manager.send_command(
        device_id=request.device_id,
        command={
            "type": "ENROLL",
            "fingerprint_id": fingerprint_id,
            "customer_id": request.customer_nuip,
        },
    )

    if not sent:
        pending_enrollments.pop(
            fingerprint_id,
            None,
        )

        raise HTTPException(
            status_code=409,
            detail="Dispositivo desconectado",
        )

    return {
        "message": "Proceso de registro iniciado",
        "fingerprint_id": fingerprint_id,
    }


async def _delete_on_device(device_id: str, print_id: int) -> dict:
    """
    Envía DELETE_FINGERPRINT al ESP32 y espera su respuesta.
    Devuelve {"ok": bool, "reason": str | None}.
    Lanza HTTPException si el dispositivo no está conectado o no responde.
    """
    if print_id in pending_deletions:
        raise HTTPException(
            status_code=409,
            detail=f"Ya hay una eliminación en curso para la huella {print_id}",
        )

    future = asyncio.get_running_loop().create_future()
    pending_deletions[print_id] = future

    try:
        sent = await manager.send_command(
            device_id=device_id,
            command={
                "type": "DELETE_FINGERPRINT",
                "fingerprint_id": print_id,
            },
        )

        if not sent:
            raise HTTPException(
                status_code=409,
                detail="Dispositivo desconectado",
            )

        try:
            return await asyncio.wait_for(future, timeout=DELETE_TIMEOUT)
        except asyncio.TimeoutError:
            raise HTTPException(
                status_code=504,
                detail="El dispositivo no respondió a tiempo",
            )

    finally:
        pending_deletions.pop(print_id, None)


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


@router.post("/attendance/start")
async def start_attendance(
    request: AttendanceRequest,
):
    sent = await manager.send_command(
        device_id=request.device_id,
        command={
            "type": "VERIFY",
        },
    )

    if not sent:
        raise HTTPException(
            status_code=409,
            detail="Dispositivo desconectado"
        )

    return {
        "message": "Proceso de validación iniciado"
    }
