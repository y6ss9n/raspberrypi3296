from __future__ import annotations

import os
import platform
import subprocess
import time
from pathlib import Path
from typing import Optional

import psutil

from .models import SystemSnapshot


def _read_model_info() -> str:
    model_paths = [
        Path("/proc/device-tree/model"),
        Path("/sys/firmware/devicetree/base/model"),
    ]
    for path in model_paths:
        try:
            if path.exists():
                return path.read_text(encoding="utf-8").strip("\x00\n")
        except OSError:
            continue
    return platform.platform()


def _read_temperature() -> Optional[float]:
    try:
        if psutil.sensors_temperatures():
            temperatures = psutil.sensors_temperatures()
            for sensor_values in temperatures.values():
                if sensor_values:
                    return float(sensor_values[0].current)
    except Exception:
        pass

    if shutil_which := subprocess.run(["which", "vcgencmd"], capture_output=True, text=True):
        if shutil_which.returncode == 0:
            result = subprocess.run(["vcgencmd", "measure_temp"], capture_output=True, text=True)
            if result.returncode == 0 and "temp=" in result.stdout:
                raw_value = result.stdout.split("temp=", 1)[1].split("'", 1)[0]
                try:
                    return float(raw_value)
                except ValueError:
                    return None
    return None


def _check_online() -> tuple[bool, Optional[float]]:
    ping_targets = ["1.1.1.1", "8.8.8.8"]
    for target in ping_targets:
        try:
            result = subprocess.run(
                ["ping", "-c", "1", "-W", "2", target],
                capture_output=True,
                text=True,
                timeout=5,
            )
        except (subprocess.SubprocessError, FileNotFoundError):
            continue
        if result.returncode == 0:
            latency = None
            for line in result.stdout.splitlines():
                if "time=" in line:
                    try:
                        latency = float(line.split("time=", 1)[1].split()[0])
                    except ValueError:
                        latency = None
                    break
            return True, latency
    return False, None


def get_system_snapshot() -> SystemSnapshot:
    cpu_usage = float(psutil.cpu_percent(interval=0.5))
    ram_usage = float(psutil.virtual_memory().percent)
    storage_usage = float(psutil.disk_usage("/").percent)
    online, latency = _check_online()
    boot_time = psutil.boot_time()
    return SystemSnapshot(
        cpu_usage=cpu_usage,
        ram_usage=ram_usage,
        storage_usage=storage_usage,
        temperature_c=_read_temperature(),
        model=_read_model_info(),
        online=online,
        latency_ms=latency,
        load_average=list(os.getloadavg()) if hasattr(os, "getloadavg") else [],
        uptime_seconds=None if not boot_time else time.time() - boot_time,
    )
