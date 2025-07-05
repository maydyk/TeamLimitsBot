import re
from typing import Optional

def even_hex(number: int) -> str:
    """
    Format number as even hex without prefix 0x
    """

    # Estimate length:
    length = len(hex(number)) - 2
    
    # Padding to even
    length += length % 2

    # apply sign
    if number < 0:
        length += 1
    
    # Format text
    return f"{number:0{length}x}".upper()


def even_hex_pattern(prefix: str) -> re.Pattern:
    """
    Build a regular expression to parse even hex string with prefix
    """
    return re.compile(f"^{prefix}((?:-?[0-9A-Fa-f]{{2}})+)$")


def even_hex_parse(pattern: re.Pattern, text: str) -> Optional[int]:
    """
    Parse [text] with pattern as hex integer.
    """
    match = pattern.search(text)
    if match:
        value = match.group(1)
        if value:
            return int(value, base=16)
    
    return None

