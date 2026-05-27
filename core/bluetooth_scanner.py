from __future__ import annotations

import re
import shutil
import subprocess
from typing import Any, Dict, List


ADDRESS_RE = re.compile(r"[0-9A-Fa-f:]{17}")


def _run(command: list[str], timeout: int = 20) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, capture_output=True, text=True, check=False, timeout=timeout)


def scan_bluetooth_devices() -> List[Dict[str, Any]]:
    if shutil.which("bluetoothctl"):
        devices = _scan_with_bluetoothctl()
        if devices:
            return devices

    if shutil.which("btmgmt"):
        return _scan_with_btmgmt()

    return []


def _scan_with_bluetoothctl() -> List[Dict[str, Any]]:
    devices: list[dict[str, Any]] = []

    known = _run(["bluetoothctl", "devices"])
    devices.extend(_parse_bluetoothctl_output(known.stdout.splitlines()))
    if devices:
        return devices

    try:
        scan = _run(["bluetoothctl", "scan", "on"], timeout=10)
        devices.extend(_parse_bluetoothctl_output(scan.stdout.splitlines()))
    except subprocess.TimeoutExpired as exc:
        output = (exc.stdout or "").splitlines() if exc.stdout else []
        devices.extend(_parse_bluetoothctl_output(output))

    return _dedupe_devices(devices)


def _scan_with_btmgmt() -> List[Dict[str, Any]]:
    try:
        result = _run(["btmgmt", "find"], timeout=15)
        return _parse_btmgmt_output(result.stdout.splitlines())
    except subprocess.TimeoutExpired as exc:
        output = (exc.stdout or "").splitlines() if exc.stdout else []
        return _parse_btmgmt_output(output)


def _parse_bluetoothctl_output(lines: list[str]) -> List[Dict[str, Any]]:
    devices: list[dict[str, Any]] = []
    for line in lines:
        stripped = line.strip()
        if not stripped.startswith("Device "):
            continue
        parts = stripped.split(maxsplit=2)
        if len(parts) < 3:
            continue
        address = parts[1]
        if not ADDRESS_RE.fullmatch(address):
            continue
        name = parts[2].strip() or address
        devices.append({"name": name, "address": address})
    return _dedupe_devices(devices)


def _parse_btmgmt_output(lines: list[str]) -> List[Dict[str, Any]]:
    devices: list[dict[str, Any]] = []
    for line in lines:
        if "dev_found" not in line:
            continue
        address_match = ADDRESS_RE.search(line)
        if not address_match:
            continue
        address = address_match.group(0)
        name = address
        if "name " in line:
            name = line.split("name ", 1)[1].strip() or address
        devices.append({"name": name, "address": address})
    return _dedupe_devices(devices)


def _dedupe_devices(devices: list[dict[str, Any]]) -> List[Dict[str, Any]]:
    seen: set[str] = set()
    unique: list[dict[str, Any]] = []
    for device in devices:
        address = device.get("address", "")
        if not address or address in seen:
            continue
        seen.add(address)
        unique.append(device)
    return unique
