"""
app/services/frontend_hub.py

Canal en tiempo real hacia las pantallas del navegador (solo lectura).
Los dispositivos siguen hablando con DeviceConnectionManager; este hub
solo repite lo que pasa para que la UI lo pinte.

Limitación: vive en memoria, así que sirve con UN solo worker de uvicorn.
Con varios workers haría falta Redis pub/sub (igual que pending_*).
"""
import asyncio
from datetime import datetime
from typing import Literal
from uuid import uuid4

from fastapi import WebSocket

DeviceKind = Literal["biometric", "camera"]
SEND_TIMEOUT = 2  # un navegador lento no debe frenar a los demás


def _now() -> str:
    # Sin zona horaria, igual que el resto de fechas de tu API.
    return datetime.now().isoformat(timespec="seconds")


class FrontendHub:
    def __init__(self) -> None:
        self._clients: set[WebSocket] = set()
        self._devices: dict[str, dict] = {}

    # ── navegadores ──
    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self._clients.add(websocket)
        # Foto inicial: así una recarga de la pantalla no pierde el estado.
        await websocket.send_json(self.snapshot())

    def disconnect(self, websocket: WebSocket) -> None:
        self._clients.discard(websocket)

    def snapshot(self) -> dict:
        return {"type": "SNAPSHOT", "devices": list(self._devices.values())}

    async def broadcast(self, event: dict) -> None:
        """Nunca lanza: un fallo de la UI no debe afectar al ESP."""
        await asyncio.gather(
            *(self._safe_send(ws, event) for ws in list(self._clients))
        )

    async def _safe_send(self, ws: WebSocket, event: dict) -> None:
        try:
            await asyncio.wait_for(ws.send_json(event), SEND_TIMEOUT)
        except Exception:
            self._clients.discard(ws)

    # ── dispositivos ──
    async def device_online(self, device_id: str, kind: DeviceKind) -> None:
        self._devices[device_id] = {
            "device_id": device_id,
            "kind": kind,
            "online": True,
            "last_seen": _now(),
        }
        await self.broadcast({"type": "DEVICE_STATUS", **self._devices[device_id]})

    async def device_offline(self, device_id: str) -> None:
        device = self._devices.get(device_id)
        if device is None:
            return
        device["online"] = False
        await self.broadcast({"type": "DEVICE_STATUS", **device})

    def touch(self, device_id: str) -> None:
        """Actualiza 'última conexión' en cada mensaje (no emite evento)."""
        if device := self._devices.get(device_id):
            device["last_seen"] = _now()


def access_event(
    *,
    device_id: str,
    granted: bool,
    access_type: str | None = None,
    reason: str | None = None,
    customer: dict | None = None,
    membership_end: str | None = None,
) -> dict:
    return {
        "type": "ACCESS_EVENT",
        "id": uuid4().hex,
        "at": _now(),
        "device_id": device_id,
        "granted": granted,
        "access_type": access_type,      # CHECK_IN | CHECK_OUT
        # CUSTOMER_NOT_FOUND | MEMBERSHIP_NOT_FOUND | FINGER_NOT_FOUND
        "reason": reason,
        "customer": customer,            # {nuip, full_name, photo_url}
        "membership_end": membership_end,
    }


hub = FrontendHub()
