"""
app/routers/events.py  (inclúyelo con app.include_router(events.router))

Se usa /events/ws y NO /devices/ws/frontend a propósito: la ruta
/devices/ws/{device_id} capturaría "frontend" como si fuera un dispositivo.
"""
from app.services.frontend_hub import hub, access_event
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.services.frontend_hub import hub

router = APIRouter(prefix="/events", tags=["events"])


@router.websocket("/ws")
async def events_ws(websocket: WebSocket):
    await hub.connect(websocket)
    try:
        while True:
            # El navegador no envía nada; esto mantiene el socket abierto
            # y detecta el cierre.
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        hub.disconnect(websocket)


@router.post("/debug/access")
async def debug_access(granted: bool = True):
    await hub.broadcast(access_event(
        device_id="esp-32", granted=granted,
        access_type="CHECK_IN" if granted else None,
        reason=None if granted else "MEMBERSHIP_NOT_FOUND",
        customer={"nuip": 123, "full_name": "Cliente de prueba", "photo_url": None}))
    return {"ok": True}
