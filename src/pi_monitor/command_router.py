from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict

from . import network, system_info
from .models import CommandRequest, CommandResponse
from .protocol import make_error, make_success


CommandHandler = Callable[[CommandRequest], CommandResponse]


@dataclass(slots=True)
class CommandRouter:
    handlers: Dict[str, CommandHandler]

    @classmethod
    def default(cls) -> "CommandRouter":
        return cls(
            handlers={
                "scan_wifi": _handle_scan_wifi,
                "scan_bluetooth": _handle_scan_bluetooth,
                "system_info": _handle_system_info,
                "connectivity": _handle_connectivity,
                "ping": _handle_connectivity,
            }
        )

    def execute(self, request: CommandRequest) -> CommandResponse:
        handler = self.handlers.get(request.command)
        if handler is None:
            return make_error(request.command, f"Unsupported command: {request.command}", request.request_id, request.source)
        try:
            response = handler(request)
            response.request_id = request.request_id
            response.source = request.source
            return response
        except Exception as exc:  # defensive boundary for transport adapters
            return make_error(request.command, str(exc), request.request_id, request.source)


def _handle_scan_wifi(request: CommandRequest) -> CommandResponse:
    networks = network.scan_wifi_networks()
    return make_success(
        request.command,
        {"networks": [item.to_dict() for item in networks], "count": len(networks)},
        request.request_id,
        request.source,
    )


def _handle_scan_bluetooth(request: CommandRequest) -> CommandResponse:
    devices = network.scan_bluetooth_devices()
    return make_success(
        request.command,
        {"devices": [item.to_dict() for item in devices], "count": len(devices)},
        request.request_id,
        request.source,
    )


def _handle_system_info(request: CommandRequest) -> CommandResponse:
    snapshot = system_info.get_system_snapshot()
    return make_success(request.command, snapshot.to_dict(), request.request_id, request.source)


def _handle_connectivity(request: CommandRequest) -> CommandResponse:
    snapshot = system_info.get_system_snapshot()
    return make_success(
        request.command,
        {"online": snapshot.online, "latency_ms": snapshot.latency_ms},
        request.request_id,
        request.source,
    )
