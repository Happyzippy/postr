from pydantic import BaseModel, validator
from typing import List, Optional


class Filter(BaseModel):
    ids: Optional[List]
    authors: Optional[List]
    
    @validator("ids", "authors", pre=True)
    def allow_single_obj(cls, values):
        if values is None:
            return values
        return values if isinstance(values, (list, tuple)) else [values]

