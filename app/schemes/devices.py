from pydantic import BaseModel


class EnrollFingerprintRequest(BaseModel):
    device_id: str = "esp-32"
    customer_nuip: int


class AttendanceRequest(BaseModel):
    device_id: str = "esp-32"


class CaptureRequest(BaseModel):
    device_id: str = "esp-cam"
    customer_nuip: int
