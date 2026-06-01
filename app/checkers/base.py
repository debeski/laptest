from dataclasses import dataclass, field
from enum import Enum


class Status(str, Enum):
    PASS    = "pass"
    WARN    = "warn"
    FAIL    = "fail"
    INFO    = "info"
    PENDING = "pending"
    RUNNING = "running"


@dataclass
class CheckResult:
    key: str
    label: str
    value: str
    status: Status
    detail: str = ""
    raw: object = field(default=None, repr=False)

    def as_dict(self) -> dict:
        return {
            "key":    self.key,
            "label":  self.label,
            "value":  self.value,
            "status": self.status.value,
            "detail": self.detail,
        }
