import asyncio
import postr


async def controller():
    user = postr.User()
    hub = postr.RelayHub()
    damus = await hub.connect("wss://relay.damus.io")

    hub.publish(
        postr.RequestMessage(subscription_id="ABC", filters=postr.Filter()),
        connection=damus,
    )
    while True:
        match message := await hub.messages.get():
            case postr.SubscriptionResponse(event=postr.TextNote()):
                event = message.event
                if event.verify():
                    print("TextNote", event.content)
            case postr.SubscriptionResponse():
                event = message.event
                if event.verify():
                    print("unknown kind", event.kind)
            case _:
                print("Received something else")

    await damus.stop()
    print("DONE")


if __name__ == "__main__":
    asyncio.run(controller())
