import json

from pydantic import BaseModel, root_validator
from typing import List

from postr.model.event import EventTypes
from postr.model.filter import Filter


class EventMessage(BaseModel):
    event: EventTypes

    def payload(self):
        return json.dumps(["EVENT", self.event])


class RequestMessage(BaseModel):
    subscription_id: str
    filters: List[Filter]

    def payload(self):
        return json.dumps(
            [
                "REQ",
                self.subscription_id,
                *map(lambda x: x.dict(exclude_unset=True), self.filters),
            ]
        )


class CloseMessage(BaseModel):
    subscription_id: str

    def payload(self):
        return json.dumps(["CLOSE", self.subscription_id])


class NoticeResponse(BaseModel):
    message: str

    def payload(self):
        return json.dumps(["NOTICE", self.message])


class EventMessageResponse(BaseModel):
    message_id: str
    retval: bool
    message: str

    def payload(self):
        return json.dumps(["OK", self.message_id, self.retval, self.message])


class SubscriptionResponse(BaseModel):
    subscription_id: str
    event: EventTypes

    def payload(self):
        return json.dumps(["EVENT", self.subscription_id, self.event])


class ParsingException(Exception):
    """Base class for parsing errors"""


class EventSignatureNotValid(Exception):
    """Event signature could not be validated"""


def parse_message(content, validate_events=True):
    match json.loads(content):
        # Client Requests
        case ["EVENT", event]:
            if validate_events and event.validate():
                raise EventSignatureNotValid()
            return EventMessage(event=event)
        case ["REQ", subscription_id, *filters]:
            return RequestMessage(subscription_id=subscription_id, filters=filters)

        # Server Responses
        case ["NOTICE", message]:
            return NoticeResponse(message=message)
        case ["OK", message_id, retval, event]:
            return EventMessageResponse(
                message_id=message_id, retval=retval, event=event
            )
        case ["EVENT", subscription_id, event]:
            return SubscriptionResponse(subscription_id=subscription_id, event=event)
    raise ParsingException(f"message could not be parsed, {content}")
