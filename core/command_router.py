from __future__ import annotations

from dataclasses import dataclass
import logging
from typing import Any, Callable, Dict

from core.bluetooth_scanner import scan_bluetooth_devices
from core.system_tools import get_system_info
from core.wifi_scanner import scan_wifi_networks
from utils.json_utils import JsonPayloadError, loads_object, make_response


CommandHandler = Callable[[Dict[str, Any]], Dict[str, Any]]


LOGGER = logging.getLogger(__name__)


@dataclass(slots=True)
class CommandRouter:
    handlers: Dict[str, CommandHandler] | None = None

    def __post_init__(self) -> None:
        if self.handlers is None:
            self.handlers = {
                "scan_wifi": self._handle_scan_wifi,
                "scan_bluetooth": self._handle_scan_bluetooth,
                "system_info": self._handle_system_info,
                "ping": self._handle_ping,
            }

    def route_raw(self, raw_payload: str, source: str = "ble") -> Dict[str, Any]:
        LOGGER.info("Incoming %s payload: %s", source, raw_payload)
        try:
            request = loads_object(raw_payload)
        except JsonPayloadError as exc:
            LOGGER.warning("Rejected %s payload: %s", source, exc)
            return make_response(command="unknown", success=False, error=str(exc), source=source)
        return self.route(request, source=source)

    def route(self, request: Dict[str, Any], source: str = "ble") -> Dict[str, Any]:
        command = request.get("command")
        request_id = request.get("request_id")
        if not isinstance(command, str) or not command.strip():
            LOGGER.warning("Rejected %s payload: missing command", source)
            return make_response(command="unknown", success=False, error="Missing command field", request_id=request_id, source=source)

        handler = self.handlers.get(command)
        if handler is None:
            LOGGER.warning("Rejected %s command: %s", source, command)
            return make_response(command=command, success=False, error=f"Unsupported command: {command}", request_id=request_id, source=source)

        params = request.get("params", {})
        if params is None:
            params = {}
        if not isinstance(params, dict):
            return make_response(command=command, success=False, error="params must be an object", request_id=request_id, source=source)

        try:
            LOGGER.info("Executing %s command", command)
            data = handler(params)
            return make_response(command=command, success=True, data=data, request_id=request_id, source=source)
        except Exception as exc:
            LOGGER.exception("Command failed: %s", command)
            return make_response(command=command, success=False, error=str(exc), request_id=request_id, source=source)

    def _handle_scan_wifi(self, _params: Dict[str, Any]) -> Dict[str, Any]:
        networks = scan_wifi_networks()
        return {"networks": networks, "count": len(networks)}

    def _handle_scan_bluetooth(self, _params: Dict[str, Any]) -> Dict[str, Any]:
        devices = scan_bluetooth_devices()
        return {"devices": devices, "count": len(devices)}

    def _handle_system_info(self, _params: Dict[str, Any]) -> Dict[str, Any]:
        return get_system_info()

    def _handle_ping(self, _params: Dict[str, Any]) -> Dict[str, Any]:
        return {"alive": True}
