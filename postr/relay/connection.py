import asyncio
import logging

import websockets
from postr.model.messages import Message, ParsingException, parse_message
from postr.relay.retry import connect_with_retry
import postr
from pydantic import ValidationError

log = logging.getLogger(__name__)


class RelayHub:
    """Set of relays to manage"""

    def __init__(self):
        self.connections = dict()
        self.messages = asyncio.Queue()

    async def connect(self, relay: str, **kwargs):
        return await RelayConnection(relay, self, **kwargs).start()

    def publish(self, message, relay: str = None):
        connection = self.connections[relay] if relay else None

        # Publish
        if connection is None:
            # on all
            for connection in self.connections.values():
                connection.queue.put_nowait(message)
        else:
            connection.queue.put_nowait(message)


class RelayConnection:
    """Single relay connection"""

    def __init__(self, relay: str, hub: RelayHub, validate_events=True) -> None:
        self.relay = relay
        self.hub = hub
        self.validate_events = validate_events
        self.queue = asyncio.Queue()
        self._active = asyncio.Event()
        self._task = None

    def __enter__(self):
        self.hub.connections[self.relay] = self
        self._active.set()
        return self.queue

    def __exit__(self, type, value, traceback):
        self._active.clear()
        del self.hub.connections[self.relay]

    async def start(self):
        """Start connection to relay"""
        self._task = asyncio.create_task(self.process())
        await self._active.wait()
        return self

    async def stop(self):
        """Stop connection to relay"""
        self._task.cancel()
        try:
            await self._task
        except asyncio.CancelledError:
            pass
        finally:
            self.task = None

    async def process(self):
        """Method for processing of connection"""
        try:
            # Register queue with hub
            with self as queue:
                # Connect and reconnect if closed
                async for websocket in connect_with_retry(self.relay):
                    try:
                        # Send and receive data on websocket
                        await asyncio.gather(
                            self.send_processor(websocket, self.queue),
                            self.recv_processor(websocket, self.hub.messages),
                        )
                    except websockets.ConnectionClosed as ex:
                        continue
        except asyncio.CancelledError as ex:
            print("I got cancelled")

    async def send_processor(self, websocket, send_queue: asyncio.Queue):
        while True:
            message = await send_queue.get()

            # Retrieve payload if object
            if hasattr(message, "payload"):
                message = message.payload()

            await websocket.send(message)

    async def recv_processor(self, websocket, message_queue: asyncio.Queue):
        while True:
            buffer = await websocket.recv()
            try:
                message = parse_message(buffer, validate_events=self.validate_events)
                message.relay = self.relay
                await message_queue.put(message)
            except (ParsingException, ValidationError) as ex:
                log.warning("Error parsing message", exc_info=ex)
