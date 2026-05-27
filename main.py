from __future__ import annotations

import asyncio
import contextlib
import logging
import signal

from ble.server import PiControlBleServer
from core.command_router import CommandRouter


LOG_FORMAT = "%(asctime)s %(levelname)s %(name)s: %(message)s"


async def run_service() -> None:
    router = CommandRouter()
    server = PiControlBleServer(router=router)
    await server.run_forever()


async def main() -> None:
    logger = logging.getLogger("pi_backend")
    while True:
        try:
            await run_service()
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Backend loop crashed; restarting in 5 seconds")
            await asyncio.sleep(5)


def entrypoint() -> None:
    logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    stop_event = asyncio.Event()

    def _stop(*_args: object) -> None:
        stop_event.set()

    for signum in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(signum, _stop)
        except NotImplementedError:
            pass

    async def _runner() -> None:
        service_task = asyncio.create_task(main())
        await stop_event.wait()
        service_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await service_task

    try:
        loop.run_until_complete(_runner())
    finally:
        loop.close()


if __name__ == "__main__":
    entrypoint()