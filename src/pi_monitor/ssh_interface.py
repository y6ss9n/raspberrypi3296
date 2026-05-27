from __future__ import annotations

from .command_router import CommandRouter
from .protocol import ProtocolError, make_error, parse_request, render_response


class SshJsonInterface:
    def __init__(self, router: CommandRouter | None = None) -> None:
        self._router = router or CommandRouter.default()

    def handle_json(self, raw_payload: str) -> str:
        request = parse_request(raw_payload)
        response = self._router.execute(request)
        return render_response(response)


def handle_ssh_payload(raw_payload: str) -> str:
    return SshJsonInterface().handle_json(raw_payload)


def run_stdin_loop() -> int:
    import sys

    payload = sys.stdin.read().strip()
    if not payload:
        sys.stderr.write("No JSON payload provided\n")
        return 1
    try:
        sys.stdout.write(handle_ssh_payload(payload) + "\n")
        return 0
    except ProtocolError as exc:
        sys.stdout.write(render_response(make_error("unknown", str(exc), source="ssh")) + "\n")
        return 2
