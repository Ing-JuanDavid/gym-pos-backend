import asyncio
import json

from app.services.device_connection_manager import manager
from app.schemes.devices import DeviceCommand
from app.helpers import device_helpers


from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.services.fingerprint import FingerPrintServiceDep

from app.services.attendance import AttendanceServiceDep

router = APIRouter(prefix="/devices", tags=["Devices"])


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
                    device_helpers._resolve_enrollment(
                        message["fingerprint_id"],
                        ok=True,
                        reason=None
                    )
                case "FINGER_DETECTED":
                    await device_helpers.handle_finger_detected(message, websocket, fingerprint_service, attendance_service)

                case "DELETE_SUCCESS":
                    device_helpers._resolve_deletion(
                        message["fingerprint_id"],
                        ok=True,
                        reason=None,
                    )

                case "ENROLL_FAILED":

                    fingerprint_id = message[
                        "fingerprint_id"
                    ]

                    device_helpers.pending_enrollments.pop(
                        fingerprint_id,
                        None,
                    )
                case "FINGER_NOT_FOUND":
                    await websocket.send_json({"type": DeviceCommand.DENY_ACCESS})

                case "DELETE_FAILED":
                    device_helpers._resolve_deletion(
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
                    device_helpers._resolve_capture(
                        device_id, error=data.get("status"))

    finally:
        manager.disconnect(device_id, websocket)


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
