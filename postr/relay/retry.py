import asyncio
import logging
import random
import websockets
from typing import AsyncIterator
from socket import gaierror
from ssl import SSLCertVerificationError

log = logging.getLogger(__name__)


async def connect_with_retry(
    ws, **kwargs
) -> AsyncIterator[websockets.WebSocketClientProtocol]:
    BACKOFF_MIN = 1.92
    BACKOFF_MAX = 60.0
    BACKOFF_FACTOR = 1.618
    BACKOFF_INITIAL = 5

    backoff_delay = BACKOFF_MIN
    while True:
        try:
            async with websockets.connect(ws, **kwargs) as websocket:
                yield websocket
        except (
            websockets.InvalidStatusCode,
            websockets.InvalidMessage,
            SSLCertVerificationError,
            gaierror,
        ):
            log.info(f"Connection failed '{ws}'")
            return
        except Exception as ex:
            # Add a random initial delay between 0 and 5 seconds.
            # See 7.2.3. Recovering from Abnormal Closure in RFC 6544.
            if backoff_delay == BACKOFF_MIN:
                initial_delay = random.random() * BACKOFF_INITIAL
                log.info(
                    "! connect failed; reconnecting in %.1f seconds",
                    initial_delay,
                    exc_info=True,
                )
                await asyncio.sleep(initial_delay)
            else:
                log.info(
                    "! connect failed again; retrying in %d seconds",
                    int(backoff_delay),
                    exc_info=True,
                )
                await asyncio.sleep(int(backoff_delay))
            # Increase delay with truncated exponential backoff.
            backoff_delay = backoff_delay * BACKOFF_FACTOR
            backoff_delay = min(backoff_delay, BACKOFF_MAX)
            continue
        else:
            # Connection succeeded - reset backoff delay
            backoff_delay = BACKOFF_MIN
