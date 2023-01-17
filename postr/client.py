import asyncio
import postr
import logging

log = logging.getLogger(__name__)

async def controller():
    user = postr.User()
    hub = postr.RelayHub()
    damus = await hub.connect("wss://relay.damus.io")

    hub.publish(
        postr.RequestMessage(subscription_id="ABC",
                             filters=postr.Filter(
                                 authors=user.username,
                                 ids=None
                                 )),
        connection=damus,
    )
    hub.publish(
        postr.EventMessage(
            event=user.sign(postr.TextNote(content="Hello there!"))
        )
    )
    
    while True:
        match message := await hub.messages.get():
            case postr.SubscriptionResponse(event=postr.TextNote()):
                event = message.event
                log.info(f"TextNote {event.content}")
            case postr.SubscriptionResponse():
                event = message.event
                log.info(f"unknown kind {event.kind}")
            case _:
                log.info("Received something else")

    await damus.stop()
    print("DONE")


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    asyncio.run(controller())
