from itertools import filterfalse
from typing import List, TypeVar

_LD = TypeVar("T")


# See https://stackoverflow.com/a/33491327/3023211
def list_difference(minuend: List[_LD], subtrahend: List[_LD]) -> List[_LD]:
    # Convert to a set for better performance.
    s = set(subtrahend)
    # inverse filtering
    return list(filterfalse(s.__contains__, minuend))

