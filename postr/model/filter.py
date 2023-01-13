from pydantic import BaseModel
from typing import List, Optional


class Filter(BaseModel):
    ids: Optional[List]
    authors: Optional[List]
