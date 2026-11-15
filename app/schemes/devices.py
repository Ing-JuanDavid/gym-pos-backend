from pydantic import BaseModel
from enum import Enum


class EnrollFingerprintRequest(BaseModel):
    device_id: str = "esp-32"
    customer_nuip: int


class AttendanceRequest(BaseModel):
    device_id: str = "esp-32"


class CaptureRequest(BaseModel):
    device_id: str = "esp-cam"
    customer_nuip: int


class DeviceCommand(str, Enum):
    ALLOW_ACCESS = "ALLOW_ACCESS"
    DENY_ACCESS = "DENY_ACCESS"
    ENROLL = "ENROLL"
    DELETE_FINGERPRINT = "DELETE_FINGERPRINT"
