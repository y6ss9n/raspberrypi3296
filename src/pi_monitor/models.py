from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(slots=True)
class CommandRequest:
    command: str
    params: Dict[str, Any] = field(default_factory=dict)
    request_id: Optional[str] = None
    source: str = "unknown"


@dataclass(slots=True)
class CommandResponse:
    success: bool
    command: str
    data: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    request_id: Optional[str] = None
    source: str = "unknown"
    timestamp: str = field(default_factory=utc_now_iso)

    def to_dict(self) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "success": self.success,
            "command": self.command,
            "data": self.data,
            "request_id": self.request_id,
            "source": self.source,
            "timestamp": self.timestamp,
        }
        if self.error is not None:
            payload["error"] = self.error
        return payload


@dataclass(slots=True)
class WifiNetwork:
    ssid: str
    signal_strength: int
    security: str = "unknown"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ssid": self.ssid,
            "signal_strength": self.signal_strength,
            "security": self.security,
        }


@dataclass(slots=True)
class BluetoothDevice:
    name: str
    address: str
    rssi: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        payload = {"name": self.name, "address": self.address}
        if self.rssi is not None:
            payload["rssi"] = self.rssi
        return payload


@dataclass(slots=True)
class SystemSnapshot:
    cpu_usage: float
    ram_usage: float
    storage_usage: float
    temperature_c: Optional[float]
    model: str
    online: bool
    latency_ms: Optional[float]
    load_average: List[float] = field(default_factory=list)
    uptime_seconds: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "cpu_usage": self.cpu_usage,
            "ram_usage": self.ram_usage,
            "storage_usage": self.storage_usage,
            "temperature_c": self.temperature_c,
            "model": self.model,
            "online": self.online,
            "latency_ms": self.latency_ms,
            "load_average": self.load_average,
            "uptime_seconds": self.uptime_seconds,
        }
