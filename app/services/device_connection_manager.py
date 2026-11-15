
from fastapi import WebSocket, WebSocketDisconnect
import asyncio


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


def get_device_connection_manager() -> DeviceConnectionManager:
    return DeviceConnectionManager()


manager = DeviceConnectionManager()
