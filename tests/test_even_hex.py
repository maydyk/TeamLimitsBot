import base
from teamlimits.details.even_hex import *

if __name__ == "__main__":
    # Test even_hex()
    assert even_hex(0) == "00"
    assert even_hex(-0) == "00"
    assert even_hex(10) == "0A"
    assert even_hex(0x30) == "30"
    assert even_hex(0x123) == "0123"
    assert even_hex(-1237) == "-04D5"
    print("even_hex() tests are completed!")

    # Test even_hex_pattern() and even_hex
    pattern = even_hex_pattern("test-")

    assert even_hex_parse(pattern, "test-0ABC") == 0xABC
    assert even_hex_parse(pattern, "test-0abc") == 0xABC
    assert even_hex_parse(pattern, "test--abcd") == -0xABCD
    assert even_hex_parse(pattern, "text-0ABC") == None
    assert even_hex_parse(pattern, "test-ABC") == None
    assert even_hex_parse(pattern, "test-xyzj") == None
    print("even_hex_parse() tests are completed!")