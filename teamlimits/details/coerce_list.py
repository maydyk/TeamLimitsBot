from typing import List, Optional, TypeVar

_CF = TypeVar("T")

def coerce_first(items: List[_CF], maximal: Optional[int]) -> List[_CF]:
    """
    Returns first maximal items from the list. Treat None as full list.
    """
    return items[: maximal if maximal is not None else len(items)]
    

def coerce_last(items: List[_CF], maximal: Optional[int]) -> List[_CF]:
    return items[maximal if maximal is not None else len(items) :]
