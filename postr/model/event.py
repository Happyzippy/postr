from pydantic import BaseModel, Field, constr, PositiveInt
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


class TextNote(Event):
    kind: Literal[1] = 1


EventTypes = TextNote | Event
