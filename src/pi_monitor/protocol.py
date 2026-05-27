from __future__ import annotations

import json
from typing import Any, Dict

from .models import CommandRequest, CommandResponse


class ProtocolError(ValueError):
    pass


ALLOWED_COMMANDS = {
    "scan_wifi",
    "scan_bluetooth",
    "system_info",
    "connectivity",
    "ping",
}


def parse_request(raw_payload: str) -> CommandRequest:
    try:
        data = json.loads(raw_payload)
    except json.JSONDecodeError as exc:
        raise ProtocolError(f"Invalid JSON payload: {exc.msg}") from exc

    if not isinstance(data, dict):
        raise ProtocolError("Payload must be a JSON object")

    command = data.get("command")
    if not isinstance(command, str) or not command.strip():
        raise ProtocolError("Missing command field")

    if command not in ALLOWED_COMMANDS:
        raise ProtocolError(f"Command not allowed: {command}")

    params = data.get("params", {})
    if params is None:
        params = {}
    if not isinstance(params, dict):
        raise ProtocolError("params must be an object")

    return CommandRequest(
        command=command,
        params=params,
        request_id=data.get("request_id"),
        source=str(data.get("source", "unknown")),
    )


def render_response(response: CommandResponse) -> str:
    return json.dumps(response.to_dict(), separators=(",", ":"), sort_keys=True)


def make_error(command: str, message: str, request_id: str | None = None, source: str = "unknown") -> CommandResponse:
    return CommandResponse(
        success=False,
        command=command,
        error=message,
        request_id=request_id,
        source=source,
    )


def make_success(command: str, data: Dict[str, Any], request_id: str | None = None, source: str = "unknown") -> CommandResponse:
    return CommandResponse(
        success=True,
        command=command,
        data=data,
        request_id=request_id,
        source=source,
    )
