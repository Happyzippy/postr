import asyncio
import postr
import logging

log = logging.getLogger(__name__)

async def parse_messages(hub: postr.RelayHub):
    """Function to parse messages as they are received"""
    while True:
        match message := await hub.messages.get():
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
                hub.publish(
                    postr.CloseMessage(subscription_id=message.subscription_id),
                    connection=message.relay,
                )
            case _:
                log.info("Received something else")


async def controller():
    user = postr.User()
    hub = postr.RelayHub()
    damus = await hub.connect("wss://relay.damus.io")
    wellorder = await hub.connect("wss://nostr-verified.wellorder.net")

    hub.publish(
        postr.RequestMessage(
            subscription_id="ABC",
            filters=postr.Filter(
                # authors=user.username,
                # ids=None,
                kinds=postr.SetMetadata,
                since=0,
                # e="test2"
            ),
        )
    )
    if False:
        hub.publish(
            postr.EventMessage(event=user.sign(postr.TextNote(content="Hello there!")))
        )

    task = asyncio.create_task(parse_messages(hub))

    await task
    await asyncio.sleep(15)
    print("##################################")

    await damus.stop()
    print("DONE")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(controller())
