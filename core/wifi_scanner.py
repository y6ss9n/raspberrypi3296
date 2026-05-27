from __future__ import annotations

import shutil
import subprocess
from typing import Any, Dict, List


def _run(command: list[str], timeout: int = 20) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, capture_output=True, text=True, check=False, timeout=timeout)


def scan_wifi_networks() -> List[Dict[str, Any]]:
    if shutil.which("nmcli"):
        result = _run(["nmcli", "-t", "-f", "SSID,SIGNAL,SECURITY", "dev", "wifi", "list"])
        networks: list[dict[str, Any]] = []
        for raw_line in result.stdout.splitlines():
            parts = raw_line.split(":")
            if len(parts) < 3:
                continue
            ssid = parts[0].strip()
            if not ssid:
                continue
            try:
                signal_strength = int(parts[1].strip())
            except ValueError:
                signal_strength = 0
            networks.append(
                {
                    "ssid": ssid,
                    "signal_strength": signal_strength,
                    "security": parts[2].strip() or "unknown",
                }
            )
        return networks

    if shutil.which("iwlist"):
        result = _run(["iwlist", "wlan0", "scan"], timeout=30)
        networks: list[dict[str, Any]] = []
        current: dict[str, Any] = {"ssid": "", "signal_strength": 0, "security": "unknown"}
        for raw_line in result.stdout.splitlines():
            line = raw_line.strip()
            if "ESSID:" in line:
                current["ssid"] = line.split("ESSID:", 1)[1].strip().strip('"')
            elif "Signal level=" in line:
                value = line.split("Signal level=", 1)[1].split()[0]
                try:
                    current["signal_strength"] = int(value)
                except ValueError:
                    current["signal_strength"] = 0
            elif "Quality=" in line and "/" in line:
                quality = line.split("Quality=", 1)[1].split()[0]
                try:
                    numerator, denominator = quality.split("/", 1)
                    current["signal_strength"] = round((float(numerator) / float(denominator)) * 100)
                except ValueError:
                    current["signal_strength"] = 0
            elif "Encryption key:" in line:
                current["security"] = "secured" if line.endswith("on") else "open"
            elif line.startswith("Cell ") and current["ssid"]:
                networks.append(dict(current))
                current = {"ssid": "", "signal_strength": 0, "security": "unknown"}
        if current["ssid"]:
            networks.append(dict(current))
        return networks

    return []
