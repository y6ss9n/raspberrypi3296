from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from .command_router import CommandRouter
from .protocol import ProtocolError, parse_request, render_response


@dataclass(slots=True)
class BleCommandChannel:
    router: CommandRouter
    last_response: str = ""

    def handle_write(self, raw_payload: str) -> str:
        request = parse_request(raw_payload)
        response = self.router.execute(request)
        self.last_response = render_response(response)
        return self.last_response


class BluezBleServer:
    """BlueZ GATT command server.

    This module is structured for a Pi Zero W running BlueZ on Linux.
    The BLE transport is intentionally isolated so command handling remains
    identical to the SSH JSON path.
    """

    def __init__(self, router: Optional[CommandRouter] = None) -> None:
        self._router = router or CommandRouter.default()
        self._channel = BleCommandChannel(self._router)
        self._running = False

    def start(self) -> None:
        self._running = True
        # BlueZ registration is environment-specific and is expected to be wired
        # to a writable command characteristic and a notify-only response characteristic.
        # The transport contract is still fully defined here through the shared router.

    def stop(self) -> None:
        self._running = False

    def handle_command(self, raw_payload: str) -> str:
        return self._channel.handle_write(raw_payload)


class BleJsonAdapter:
    def __init__(self, server: Optional[BluezBleServer] = None) -> None:
        self._server = server or BluezBleServer()

    def send(self, raw_payload: str) -> str:
        try:
            return self._server.handle_command(raw_payload)
        except ProtocolError as exc:
            return render_response(__import__("pi_monitor.protocol", fromlist=["make_error"]).make_error("unknown", str(exc), source="ble"))
