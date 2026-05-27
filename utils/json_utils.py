from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Dict


class JsonPayloadError(ValueError):
    pass


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def loads_object(raw_payload: str) -> Dict[str, Any]:
    try:
        data = json.loads(raw_payload)
    except json.JSONDecodeError as exc:
        raise JsonPayloadError(f"Invalid JSON payload: {exc.msg}") from exc

    if not isinstance(data, dict):
        raise JsonPayloadError("Payload must be a JSON object")
    return data


def dumps_object(payload: Dict[str, Any]) -> str:
    return json.dumps(payload, separators=(",", ":"), ensure_ascii=False, sort_keys=True)


def make_response(
    *,
    command: str,
    success: bool,
    data: Dict[str, Any] | None = None,
    error: str | None = None,
    request_id: str | None = None,
    source: str = "ble",
) -> Dict[str, Any]:
    response: Dict[str, Any] = {
        "command": command,
        "success": success,
        "source": source,
        "timestamp": utc_now_iso(),
        "data": data or {},
    }
    if request_id is not None:
        response["request_id"] = request_id
    if error is not None:
        response["error"] = error
    return response
