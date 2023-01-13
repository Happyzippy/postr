from pydantic import BaseModel, Field
from typing import List, Optional, Union, Literal

import coincurve as cc
from coincurve.utils import sha256
import json
from datetime import datetime
import time


class Event(BaseModel):
    id: Optional[str]
    sig: Optional[str]
    pubkey: Optional[str]
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


EventTypes = Union[TextNote, Event]
