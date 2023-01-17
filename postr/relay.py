import asyncio
import websockets
from postr.model.messages import parse_message, ParsingException, Message
import logging

log = logging.getLogger(__name__)


class RelayHub:
    """Set of relays to manage"""

    def __init__(self):
        self.connections = set()
        self.messages = asyncio.Queue()

    async def connect(self, relay: str, **kwargs):
        return await RelayConnection(relay, self, **kwargs).start()

    def publish(self, message, connection=None):
        # If message retrieve payload
        if isinstance(message, Message):
            message = message.payload()

        # Publish
        if connection is None:
            # on all
            for connection in self.connections:
                connection.queue.put_nowait(message)
        else:
            if connection not in self.connections:
                raise KeyError("Connection not in active connections on this hub")
            connection.queue.put_nowait(message)


class RelayConnection:
    """Single relay connection"""

    def __init__(self, relay: str, hub: RelayHub, verify_events=True) -> None:
        self.relay = relay
        self.hub = hub
        self.verify_events = verify_events
        self.queue = asyncio.Queue()
        self._active = asyncio.Event()
        self._task = None

    def __enter__(self):
        self.hub.connections.add(self)
        self._active.set()
        return self.queue

    def __exit__(self, type, value, traceback):
        self._active.clear()
        self.hub.connections.discard(self)

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
                async for websocket in websockets.connect(self.relay):
                    try:
                        # Send and receive data on websocket
                        await asyncio.gather(
                            self.send_processor(websocket, self.queue),
                            self.recv_processor(websocket, self.hub.messages),
                        )
                    except websockets.ConnectionClosed:
                        continue
        except asyncio.CancelledError:
            print("I got cancelled")

    async def recv_processor(self, websocket, message_queue: asyncio.Queue):
        while True:
            buffer = await websocket.recv()
            try:
                message = parse_message(buffer)
                await message_queue.put(message)
            except ParsingException as ex:
                log.warning("Error parsing message", exc_info=ex)

    async def send_processor(self, websocket, send_queue: asyncio.Queue):
        while True:
            msg = await send_queue.get()
            await websocket.send(msg)
