import base

from teamlimits.details.list_difference import *

if __name__ == "__main__":
    # Test list_difference
    assert list_difference([], []) == []
    assert list_difference([1, 2, 3, 3, 4, 5], []) == [1, 2, 3, 3, 4, 5]
    assert list_difference([], [1, 2, 3, 3, 4, 5]) == []
    assert list_difference([1, 2, 3, 3, 4, 5], [6, 7, 8, 8]) == [1, 2, 3, 3, 4, 5]
    assert list_difference([1, 2, 3, 3, 4, 5], [1, 2, 3]) == [4, 5]
    print("list_difference() tests are completed!")

    # Test list_intersection
    assert list_intersection([], []) == []
    assert list_intersection([1, 2, 3, 3, 4, 5], []) == []
    assert list_intersection([], [1, 2, 3, 4, 5]) == []
    assert list_intersection([1, 2, 3, 3, 4, 5], [6, 7, 8, 8]) == []
    assert list_intersection([1, 2, 3, 3, 4, 5], [1, 2, 3]) == [1, 2, 3, 3]
    print("list_intersection() tests are completed!")
