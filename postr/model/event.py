from pydantic import BaseModel, Field, constr, PositiveInt, AnyUrl, validator
from typing import List, Optional, Literal

import coincurve as cc
from coincurve.utils import sha256
import json
import time

_constr_32hex = constr(min_length=64, max_length=64)
_constr_64hex = constr(min_length=128, max_length=128)


class Event(BaseModel):
    """NIP-01 Event"""

    id: Optional[_constr_32hex]
    sig: Optional[_constr_64hex]
    pubkey: Optional[_constr_32hex]
    created_at: int = Field(default_factory=lambda: int(time.time()))
    kind: int
    tags: List[List[str]] = Field(default_factory=list)
    content: str

    @property
    def event_data_hash(self):
        return sha256(
            json.dumps(
                [
                    0,
                    self.pubkey,
                    self.created_at,
                    self.kind,
                    self.tags,
                    self.content,
                ],
                separators=(",", ":"),
            ).encode()
        )

    def verify(self):
        key = cc.PublicKeyXOnly(bytes.fromhex(self.pubkey))
        return key.verify(bytes.fromhex(self.sig), self.event_data_hash)


class UserMetadata(BaseModel):
    name: Optional[str]
    about: Optional[str]
    picture: Optional[str]
    nip05: Optional[str]


class SetMetadata(Event):
    kind: Literal[0] = 0
    content: UserMetadata

    @validator("content", pre=True)
    def parse_content(cls, value):
        if type(value) == str:
            return json.loads(value)
        return value

    class Config:
        json_encoders = {
            UserMetadata: lambda x: x.json(),
        }


class TextNote(Event):
    kind: Literal[1] = 1


class AnyWsUrl(AnyUrl):
    allowed_schemes = {"ws", "wss"}
    __slots__ = ()


class RecommendServer(Event):
    kind: Literal[2] = 2
    content: AnyWsUrl

    @property
    def url(self):
        return self.content


EventTypes = TextNote | SetMetadata | RecommendServer | Event
