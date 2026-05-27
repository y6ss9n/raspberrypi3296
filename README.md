# Pi Backend

Python service for Raspberry Pi Zero W.

## Features

- BLE GATT command channel backed by BlueZ
- SSH-friendly JSON command runner
- Wi-Fi scan, Bluetooth scan, connectivity, and system metrics
- Allowlisted JSON command routing

## Run

```bash
python -m pi_monitor --help
```

For SSH usage, invoke the JSON command runner over a remote shell session and read the JSON response from stdout.
