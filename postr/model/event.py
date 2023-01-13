from pydantic import BaseModel
from typing import List, Optional, Union, Literal

import coincurve as cc
from coincurve.utils import sha256
import json
from datetime import datetime


class Event(BaseModel):
    id: Optional[str]
    sig: Optional[str]
    pubkey: str
    created_at: int
    kind: int
    tags: List[List[str]]
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

    def prepare(self, private_key: cc.PrivateKey):
        event_data_hash = self.event_data_hash
        self.id = event_data_hash.hex()
        self.sig = private_key.sign_schnorr(event_data_hash).hex()
        return self

    def verify(self):
        key = cc.PublicKeyXOnly(bytes.fromhex(self.pubkey))
        return key.verify(bytes.fromhex(self.sig), self.event_data_hash)

    @classmethod
    def build(cls, private_key, content, tags=None):
        note = cls(
            pubkey=private_key.public_key_xonly.format().hex(),
            created_at=datetime.utcnow().timestamp(),
            tags=[] if tags is None else tags,
            content=content,
        )
        return note.prepare(private_key)


class TextNote(Event):
    kind: Literal[1] = 1


EventTypes = Union[TextNote, Event]
