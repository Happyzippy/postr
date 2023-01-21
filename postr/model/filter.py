from pydantic import BaseModel, validator, Field
import pydantic
from typing import List, Optional


class Filter(BaseModel):
    ids: Optional[List[str]]
    authors: Optional[List[str]]
    kinds: Optional[List[int]]
    e: Optional[List[str]] = Field(
        alias="#e",
    )
    p: Optional[List[str]] = Field(alias="#p")
    since: Optional[int]
    until: Optional[int]
    limit: Optional[int]

    @validator("kinds", pre=True, each_item=True)
    def expand_kinds(cls, value):
        if type(value) == pydantic.main.ModelMetaclass:
            return value.__fields__["kind"].default
        return value

    @validator("ids", "authors", "kinds", "e", "p", pre=True)
    def allow_single_obj(cls, values):
        if values is None:
            return values
        return values if isinstance(values, (list, tuple)) else [values]

    class Config:
        allow_population_by_field_name = True
