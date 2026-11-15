from enum import Enum


class DeviceCommand(str, Enum):
    ALLOW_ACCESS = "ALLOW_ACCESS"
    DENY_ACCESS = "DENY_ACCESS"
    ENROLL = "ENROLL"
    DELETE_FINGERPRINT = "DELETE_FINGERPRINT"
