# Access to teamlimits packages
import base

from teamlimits.details.coerce_list import *

if __name__ == "__main__":
    source = [1, 2, 3, 4, 5, 6]

    # Test coerce_first()
    assert coerce_first(source, 3) == [1, 2, 3]
    assert coerce_first(source, -2) == [1, 2, 3, 4]
    assert coerce_first(source, 0) == []
    assert coerce_first(source, 666) == source
    assert coerce_first(source, -666) == []
    assert coerce_first(source, None) == source
    print("coerce_first() tests are completed!")

    # Test coerce_last()
    assert coerce_last(source, 3) == [4, 5, 6]
    assert coerce_last(source, -2) == [5, 6]
    assert coerce_last(source, 0) == source
    assert coerce_last(source, 666) == []
    assert coerce_last(source, -666) == source
    assert coerce_last(source, None) == []
    print("coerce_last() tests are completed!")
