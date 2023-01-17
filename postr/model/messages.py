import json
from abc import ABC, abstractmethod

from pydantic import BaseModel, validator
from typing import List

from postr.model.event import EventTypes
from postr.model.filter import Filter


class Message(BaseModel, ABC):
    """Abstract baseclass for messages"""

    @abstractmethod
    def payload(self) -> str:
        """Return payload of message as string"""


class EventMessage(Message):
    event: EventTypes

    def payload(self):
        return json.dumps(["EVENT", self.event.dict()])


class RequestMessage(Message):
    subscription_id: str
    filters: List[Filter]

    @validator("filters", pre=True)
    def allow_single_obj(cls, values):
        return values if isinstance(values, (list, tuple)) else [values]

    def payload(self):
        return json.dumps(
            [
                "REQ",
                self.subscription_id,
                *map(lambda x: x.dict(exclude_unset=True), self.filters),
            ]
        )


class CloseMessage(Message):
    subscription_id: str

    def payload(self):
        return json.dumps(["CLOSE", self.subscription_id])


class NoticeResponse(Message):
    message: str

    def payload(self):
        return json.dumps(["NOTICE", self.message])


class EventMessageResponse(Message):
    message_id: str
    retval: bool
    message: str

    def payload(self):
        return json.dumps(["OK", self.message_id, self.retval, self.message])


class SubscriptionResponse(Message):
    subscription_id: str
    event: EventTypes

    def payload(self):
        return json.dumps(["EVENT", self.subscription_id, self.event.dict()])


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
        case ["CLOSE", subscription_id]:
            return CloseMessage(subscription_id=subscription_id)

        # Server Responses
        case ["NOTICE", message]:
            return NoticeResponse(message=message)
        case ["OK", message_id, retval, message]:
            return EventMessageResponse(
                message_id=message_id, retval=retval, message=message
            )
        case ["EVENT", subscription_id, event]:
            return SubscriptionResponse(subscription_id=subscription_id, event=event)
    raise ParsingException(f"message could not be parsed, {content}")
