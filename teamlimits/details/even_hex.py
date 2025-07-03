import re
from typing import Optional

def even_hex(number: int) -> str:
    """
    Format number as even hex without prefix
    """

    # Remove prefix 0x
    text = hex(number)[2:].upper()
    # Pad by zero
    l = len(text)
    return text.rjust(l + (l % 2), '0')


def even_hex_pattern(prefix: str) -> re.Pattern:
    """
    Build a regular expression to parse even hex string with prefix
    """
    return re.compile(f"^{prefix}((?:[0-9A-Fa-f]{{2}})+)$")


def even_hex_parse(pattern: re.Pattern, text: str) -> Optional[str]:
    match = pattern.search(text)
    if match:
        value = match.group(1)
        if value:
            return int(value, 16)
    
    return None

