from app.services.frontend_hub import hub, access_event
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
async def device_websocket(websocket: WebSocket, device_id: str,
                           fingerprint_service: FingerPrintServiceDep,
                           attendance_service: AttendanceServiceDep):
    await manager.connect(device_id, websocket)
    await hub.device_online(device_id, "biometric")

    try:
        while True:
            message = await websocket.receive_json()
            hub.touch(device_id)
            event_type = message.get("type")

            match event_type:
                case "ENROLL_STATUS":          # pasos: PLACE_FINGER, REMOVE_FINGER, ...
                    await hub.broadcast({"type": "ENROLL_STATUS",
                                         "device_id": device_id,
                                         "status": message.get("status")})
                case "ENROLL_SUCCESS":
                    device_helpers._resolve_enrollment(
                        message["fingerprint_id"], ok=True, reason=None)
                    await hub.broadcast({"type": "ENROLL_SUCCESS", "device_id": device_id})

                case "ENROLL_FAILED":
                    # Antes se hacía pop() del future: el endpoint esperaba los 15 s
                    # completos y respondía "no respondió a tiempo", perdiendo el motivo.
                    device_helpers._resolve_enrollment(
                        message["fingerprint_id"], ok=False, reason=message.get("status"))
                    await hub.broadcast({"type": "ENROLL_FAILED",
                                         "device_id": device_id,
                                         "status": message.get("status")})

                case "FINGER_DETECTED":
                    await hub.broadcast({"type": "READING", "device_id": device_id})
                    await device_helpers.handle_finger_detected(
                        message, websocket, fingerprint_service,
                        attendance_service, device_id)

                case "FINGER_NOT_FOUND":
                    await websocket.send_json({"type": DeviceCommand.DENY_ACCESS})
                    await hub.broadcast(access_event(
                        device_id=device_id, granted=False, reason="FINGER_NOT_FOUND"))

                case "DELETE_SUCCESS":
                    device_helpers._resolve_deletion(
                        message["fingerprint_id"], ok=True, reason=None)

                case "DELETE_FAILED":
                    device_helpers._resolve_deletion(
                        message["fingerprint_id"], ok=False, reason=message.get("status"))

    except WebSocketDisconnect:
        pass
    finally:
        manager.disconnect(device_id, websocket)
        # Si el ESP ya reconectó con otro socket, no lo marques como caído.
        if device_id not in manager.active_devices:
            await hub.device_offline(device_id)


@router.websocket("/ws/cam/{device_id}")
async def camera_websocket(websocket: WebSocket, device_id: str):
    """
    WebSocket del ESP32-CAM (órdenes y eventos, en JSON).
    La imagen NO viaja por aquí: el ESP32-CAM la sube por HTTP a
    POST /devices/captures/upload/{device_id}.
    """
    await manager.connect(device_id, websocket)
    await hub.device_online(device_id, "camera")

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
                hub.touch(device_id)

    finally:
        manager.disconnect(device_id, websocket)
        if device_id not in manager.active_devices:
            await hub.device_offline(device_id)


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
