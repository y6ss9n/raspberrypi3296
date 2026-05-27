# Pi Backend

This directory contains the Raspberry Pi Zero W backend service.

## Layout

- `install.sh`: idempotent installer for Raspberry Pi OS Lite
- `main.py`: persistent backend entrypoint
- `ble/server.py`: BlueZ GATT peripheral and notification response path
- `core/command_router.py`: strict JSON command router
- `core/system_tools.py`: CPU, RAM, storage, temperature, model, and connectivity helpers
- `core/wifi_scanner.py`: Wi-Fi network scanning helpers
- `core/bluetooth_scanner.py`: nearby Bluetooth device scanning helpers
- `utils/json_utils.py`: JSON parsing and response helpers
- `pi-backend.service`: systemd unit template

## Commands

- `scan_wifi`
- `scan_bluetooth`
- `system_info`
- `ping`

## Installation

Run the installer on Raspberry Pi OS Lite:

```bash
sudo bash install.sh
```

The installer copies this backend to `/opt/pi_backend`, creates `/opt/pi_backend/venv`, installs dependencies only inside the venv, and registers `pi-backend.service` with systemd.
