"""
Module model_fields
Extracts field name from pydantic model
"""

from dataclasses import dataclass
from functools import lru_cache
from pydantic import BaseModel
from typing import Any, TypeVar, cast, TYPE_CHECKING

# Get names of models fields
# See https://github.com/pydantic/pydantic/discussions/8600#discussioncomment-8212526

@dataclass(frozen=True)
class _GetFields:
    _model: type[BaseModel]

    def __getattr__(self, item: str) -> Any:
        # check regular fields
        if item in self._model.model_fields:
            return item
        
        # check computed fields
        if item in self._model.model_computed_fields:
            return item

        return getattr(self._model, item)


TModel = TypeVar("TModel", bound=BaseModel)


def fields(model: type[TModel], /) -> TModel:
    return cast(TModel, _GetFields(model))


if not TYPE_CHECKING:
    fields = lru_cache(maxsize=256)(fields)
