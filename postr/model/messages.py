import json
from abc import ABC, abstractmethod, abstractproperty
from uuid import uuid4
from pydantic import BaseModel, Field, validator
from typing import List, Optional

from postr.model.event import EventTypes
from postr.model.filter import Filter

_subscription_id_field = Field(
    default_factory=lambda: str(uuid4()), description="Subscription id"
)


class Message(BaseModel, ABC):
    """Abstract baseclass for messages"""

    relay: Optional[str] = Field(
        description="Metadata field about which relay the message came from"
    )
    response_to: Optional["Message"] = Field(
        description="Metadata field about which message this message is a response to"
    )

    @abstractmethod
    def payload(self) -> str:
        """Return payload of message as string"""


class EventMessage(Message):
    event: EventTypes

    @property
    def message_id(self):
        return self.event.id

    def payload(self):
        return json.dumps(["EVENT", self.event.dict()])


class RequestMessage(Message):
    message_id: str = _subscription_id_field
    filters: List[Filter]

    @validator("filters", pre=True)
    def allow_single_obj(cls, values):
        return values if isinstance(values, (list, tuple)) else [values]

    def payload(self):
        return json.dumps(
            [
                "REQ",
                self.message_id,
                *map(lambda x: x.dict(exclude_unset=True, by_alias=True), self.filters),
            ]
        )


class CloseMessage(Message):
    message_id: str = _subscription_id_field

    def payload(self):
        return json.dumps(["CLOSE", self.message_id])


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
    message_id: str = _subscription_id_field
    event: EventTypes

    def payload(self):
        return json.dumps(["EVENT", self.message_id, self.event.dict()])


class EndOfStoredEventsResponse(Message):
    """NIP-15: indicates all the events that come after this message are newly published"""

    message_id: str = _subscription_id_field

    def payload(self):
        return json.dumps(["EOSE", self.message_id])


class ParsingException(Exception):
    """Base class for parsing errors"""


class EventSignatureNotValid(Exception):
    """Event signature could not be validated"""


def parse_message(content, validate_events=True) -> Message:
    """Message parsing function, parsing all responses from through Nostr building the relevant classes"""
    match json.loads(content):
        # Client Requests
        case ["EVENT", event]:
            if validate_events and event.validate():
                raise EventSignatureNotValid()
            return EventMessage(event=event)
        case ["REQ", message_id, *filters]:
            return RequestMessage(message_id=message_id, filters=filters)
        case ["CLOSE", message_id]:
            return CloseMessage(message_id=message_id)

        # Server Responses
        case ["NOTICE", message]:
            return NoticeResponse(message=message)
        case ["OK", message_id, retval, message]:
            return EventMessageResponse(
                message_id=message_id, retval=retval, message=message
            )
        case ["EVENT", message_id, event]:
            return SubscriptionResponse(message_id=message_id, event=event)
        case ["EOSE", message_id]:
            return EndOfStoredEventsResponse(message_id=message_id)
    raise ParsingException(f"message could not be parsed, {content}")
