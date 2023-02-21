import asyncio
import postr
import logging
from pydantic import BaseModel, Field, PrivateAttr
from typing import Set, List

log = logging.getLogger(__name__)


class ClientState:
    def __init__(self) -> None:
        self.requests = dict()


class NostrClient(BaseModel):
    relays: Set[str]

    user: postr.User = Field(default_factory=postr.User)

    _hub: postr.RelayHub = PrivateAttr(default_factory=postr.RelayHub)
    _message_handler_task: asyncio.Task = PrivateAttr(None)

    @property
    def hub(self):
        return self._hub

    async def __aenter__(self) -> "NostrClient":
        self._message_handler_task = asyncio.create_task(self._message_handler())
        for relay in self.relays:
            await self.hub.connect(relay)
        return self

    async def __aexit__(self, exc_t, exc_v, exc_tb):
        # Cancel running tasks on relay
        self._message_handler_task.cancel()
        stopper_task = asyncio.gather(
            *filter(
                bool,
                [
                    *(c.stop() for c in self.hub.connections.values()),
                    self._message_handler_task,
                ],
            ),
            return_exceptions=True,
        )
        await stopper_task
        self._message_handler_task = None

    def reraise_handler_errors(self):
        if self._message_handler_task.done() and (ex := self._message_handler_task.exception()):
            raise ex

    async def add_relay(self, relay: str):
        await self.hub.connect(relay)

    async def remove_relay(self, relay: str):
        await self.hub.connections[relay].stop()

    def publish(self, event: postr.EventTypes, to=None):
        event = self.user.sign(event)
        message = postr.EventMessage(event=event)
        self.hub.publish(message, relay=to)

    def request(self, filters: postr.Filter | List[postr.Filter], to=None):
        message = postr.RequestMessage(filters=filters)
        self.hub.publish(message, relay=to)
        return message.message_id

    def stop_request(self, message_id: str, to=None):
        message = postr.CloseMessage(message_id=message_id)
        self.hub.publish(message, relay=to)

    async def _message_handler(self):
        """Function to parse messages as they are received"""
        while True:
            match message := await self.hub.messages.get():
                case postr.SubscriptionResponse(event=postr.TextNote()):
                    event = message.event
                    log.info(f"TextNote {event.content}")
                case postr.SubscriptionResponse(event=postr.RecommendServer()):
                    event = message.event
                    known = set(map(lambda x: x.relay, hub.connections))
                    if event.url not in known:
                        log.info(f"Connecting to '{event.url}'")
                        socket = await hub.connect(event.url)
                case postr.SubscriptionResponse(event=postr.SetMetadata()):
                    event = message.event
                    log.info(f"Set Metadata: {event.content}")
                case postr.SubscriptionResponse():
                    event = message.event
                    log.info(f"unknown kind {event.kind}")
                case postr.EndOfStoredEventsResponse():
                    log.info("Closing subscription at end of stored events")
                    self.stop_request(message_id=message.message_id)
                case postr.EventMessageResponse(retval=False):
                    log.warning(f"{message.relay}: '{message.message}'")
                case _:
                    log.info(message.payload)


async def main():
    async with NostrClient(
        relays=[
            "wss://relay.damus.io",
            #"wss://nostr-verified.wellorder.net",
        ]
    ) as client:
        client.request(postr.Filter(authors=client.user.username))
        client.publish(postr.TextNote(content="Hello World!"))

        # Keep running
        while True:
            await asyncio.sleep(1)
            client.reraise_handler_errors()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())