from __future__ import annotations

import argparse
import sys
import time

from .ble_service import BluezBleServer
from .command_router import CommandRouter
from .protocol import ProtocolError, make_error, parse_request, render_response
from .ssh_interface import run_stdin_loop


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Raspberry Pi monitor backend")
    parser.add_argument("--json", help="Execute a single JSON command and print the JSON response")
    parser.add_argument("--stdin", action="store_true", help="Read one JSON command from stdin")
    parser.add_argument("--ble", action="store_true", help="Start the BLE command service")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    router = CommandRouter.default()

    if args.ble:
        server = BluezBleServer(router)
        server.start()
        print("BLE command service started")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            server.stop()
        return 0

    if args.stdin:
        return run_stdin_loop()

    if args.json:
        try:
            request = parse_request(args.json)
            response = router.execute(request)
            print(render_response(response))
            return 0
        except ProtocolError as exc:
            print(render_response(make_error("unknown", str(exc), source="cli")))
            return 2

    build_parser().print_help(sys.stderr)
    return 1
