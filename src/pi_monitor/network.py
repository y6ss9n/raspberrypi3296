from __future__ import annotations

import re
import shutil
import subprocess
from typing import List

from .models import BluetoothDevice, WifiNetwork


_WPA_SIGNAL_RE = re.compile(r"(?:Signal level|Quality)=([^\n]+)", re.IGNORECASE)


def _run_command(command: list[str], timeout: int = 20) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        check=False,
        capture_output=True,
        text=True,
        timeout=timeout,
    )


def scan_wifi_networks() -> list[WifiNetwork]:
    if shutil.which("nmcli"):
        result = _run_command(["nmcli", "-t", "-f", "SSID,SIGNAL,SECURITY", "dev", "wifi", "list"])
        networks: list[WifiNetwork] = []
        for line in result.stdout.splitlines():
            parts = line.split(":")
            if len(parts) < 3:
                continue
            ssid = parts[0].strip()
            signal = parts[1].strip()
            security = parts[2].strip() or "unknown"
            if not ssid:
                continue
            try:
                signal_strength = int(signal)
            except ValueError:
                signal_strength = 0
            networks.append(WifiNetwork(ssid=ssid, signal_strength=signal_strength, security=security))
        return networks

    if shutil.which("iwlist"):
        result = _run_command(["iwlist", "wlan0", "scan"], timeout=30)
        networks = []
        current_ssid = ""
        current_signal = 0
        current_security = "unknown"
        for raw_line in result.stdout.splitlines():
            line = raw_line.strip()
            if "ESSID:" in line:
                current_ssid = line.split("ESSID:", 1)[1].strip().strip('"')
            elif "Signal level=" in line or "Quality=" in line:
                match = _WPA_SIGNAL_RE.search(line)
                if match:
                    value = match.group(1)
                    if "/" in value:
                        numerator, denominator = value.split("/", 1)
                        try:
                            current_signal = round((float(numerator) / float(denominator)) * 100)
                        except ValueError:
                            current_signal = 0
                    else:
                        try:
                            current_signal = int(value.split()[0])
                        except ValueError:
                            current_signal = 0
            elif "Encryption key:" in line:
                current_security = "secured" if line.endswith("on") else "open"
            elif line.startswith("Cell ") and current_ssid:
                networks.append(WifiNetwork(ssid=current_ssid, signal_strength=current_signal, security=current_security))
                current_ssid = ""
                current_signal = 0
                current_security = "unknown"
        if current_ssid:
            networks.append(WifiNetwork(ssid=current_ssid, signal_strength=current_signal, security=current_security))
        return networks

    return []


def scan_bluetooth_devices() -> list[BluetoothDevice]:
    if shutil.which("bluetoothctl"):
        result = _run_command(["bluetoothctl", "devices"])
        devices: list[BluetoothDevice] = []
        for line in result.stdout.splitlines():
            parts = line.strip().split(maxsplit=2)
            if len(parts) < 3 or parts[0] != "Device":
                continue
            address = parts[1]
            name = parts[2]
            devices.append(BluetoothDevice(name=name, address=address))
        return devices

    if shutil.which("btmgmt"):
        result = _run_command(["btmgmt", "find"], timeout=30)
        devices = []
        for line in result.stdout.splitlines():
            line = line.strip()
            if "dev_found" not in line:
                continue
            chunks = line.split()
            address = next((chunk for chunk in chunks if re.fullmatch(r"[0-9A-Fa-f:]{17}", chunk)), "")
            name = line.split("name ", 1)[1].strip() if "name " in line else address
            if address:
                devices.append(BluetoothDevice(name=name or address, address=address))
        return devices

    return []
