from app.services.customer import CustomerService
import asyncio

from collections import defaultdict, deque
from typing import Literal

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from app.services.customer import CustomerServiceDep
from app.services.fingerprint import FingerPrintServiceDep
from app.utilities.exceptions import not_found
from app.services.fingerprint import FingerPrintService
from app.schemes.fingerprint import FingerPrintCreate

router = APIRouter(prefix="/devices", tags=["Devices"])

# Prototipo: cola temporal en memoria por dispositivo.
commands = defaultdict(deque)


class CommandCreate(BaseModel):
    device_id: str
    action: Literal["LED_ON", "LED_OFF"]


class EnrollFingerprintRequest(BaseModel):
    device_id: str
    customer_id: int


pending_enrollments: dict[int, dict] = {}


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


@router.websocket("/ws/{device_id}")
async def device_websocket(
    websocket: WebSocket,
    device_id: str,
    fingerprint_service: FingerPrintServiceDep
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

            elif event_type == "ENROLL_FAILED":

                fingerprint_id = message[
                    "fingerprint_id"
                ]

                pending_enrollments.pop(
                    fingerprint_id,
                    None,
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

    db_customer = customer_service.get_customer_id(request.customer_id)

    if not db_customer:
        raise not_found("customer")

    fingerprint_id = fingerprint_service.get_fingerprint_id()

    pending_enrollments[fingerprint_id] = {
        "customer_id": request.customer_id,
    }

    sent = await manager.send_command(
        device_id=request.device_id,
        command={
            "type": "ENROLL",
            "fingerprint_id": fingerprint_id,
            "customer_id": request.customer_id,
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
