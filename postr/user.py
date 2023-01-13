from pydantic import BaseModel, PrivateAttr, Field
from pathlib import Path
from typing import Optional, Any

import coincurve as cc
from postr.model.event import Event


class User(BaseModel):
    """User class for managing identity and keys"""

    identity: Optional[Path] = Field(
        description="Path to .pem/.der certificates or leave empty to generate new identity"
    )
    _private_key = PrivateAttr()

    def __init__(self, **data: Any):
        super().__init__(**data)
        self._load_identity()

    def _load_identity(self):
        """Initialize identity from pem/der certificates or generate a new one if None is supplied"""
        match self.identity:
            case None:
                self._private_key = cc.PrivateKey()
            case Path(suffix=".pem"):
                with open(self.identity, "rb") as fp:
                    self._private_key = cc.PrivateKey.from_pem(fp.read())
            case Path(suffix=".der"):
                with open(self.identity, "rb") as fp:
                    self._private_key = cc.PrivateKey.from_der(fp.read())
            case _:
                raise ValueError("Identity type not recognized")

    @property
    def username(self):
        """username (public key)"""
        return self._private_key.public_key_xonly.format().hex()

    def sign(self, event: Event):
        """Sign an event"""
        event.pubkey = self.username
        event_data_hash = event.event_data_hash
        event.id = event_data_hash.hex()
        event.sig = self._private_key.sign_schnorr(event_data_hash).hex()
        return event
