from __future__ import annotations

import os
import platform
import shutil
import socket
import subprocess
import time
from pathlib import Path
from typing import Any, Dict, Optional

import psutil


def _read_model() -> str:
    for candidate in (
        Path("/proc/device-tree/model"),
        Path("/sys/firmware/devicetree/base/model"),
    ):
        try:
            if candidate.exists():
                return candidate.read_text(encoding="utf-8").strip("\x00\n")
        except OSError:
            continue
    return platform.platform()


def _read_temperature() -> Optional[float]:
    try:
        sensor_map = psutil.sensors_temperatures()
        for sensor_values in sensor_map.values():
            if sensor_values:
                return float(sensor_values[0].current)
    except Exception:
        pass

    if shutil.which("vcgencmd"):
        result = subprocess.run(["vcgencmd", "measure_temp"], capture_output=True, text=True, check=False)
        if result.returncode == 0 and "temp=" in result.stdout:
            raw_value = result.stdout.split("temp=", 1)[1].split("'", 1)[0]
            try:
                return float(raw_value)
            except ValueError:
                return None
    return None


def _check_internet() -> tuple[bool, Optional[float]]:
    for host in ("1.1.1.1", "8.8.8.8"):
        try:
            result = subprocess.run(
                ["ping", "-c", "1", "-W", "2", host],
                capture_output=True,
                text=True,
                timeout=6,
                check=False,
            )
        except (FileNotFoundError, subprocess.SubprocessError):
            continue

        if result.returncode == 0:
            latency_ms = None
            for line in result.stdout.splitlines():
                if "time=" in line:
                    try:
                        latency_ms = float(line.split("time=", 1)[1].split()[0])
                    except ValueError:
                        latency_ms = None
                    break
            return True, latency_ms
    return False, None


def get_system_info() -> Dict[str, Any]:
    internet_status, latency_ms = _check_internet()
    boot_time = psutil.boot_time()
    return {
        "cpu_usage": float(psutil.cpu_percent(interval=0.5)),
        "ram_usage": float(psutil.virtual_memory().percent),
        "storage_usage": float(psutil.disk_usage("/").percent),
        "temperature_c": _read_temperature(),
        "model": _read_model(),
        "internet_status": "online" if internet_status else "offline",
        "latency_ms": latency_ms,
        "load_average": list(os.getloadavg()) if hasattr(os, "getloadavg") else [],
        "uptime_seconds": None if not boot_time else time.time() - boot_time,
        "hostname": socket.gethostname(),
    }
