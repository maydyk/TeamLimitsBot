
from re import Pattern
from typeguard import typechecked
from typing import Optional, Self, Type, TypeVar
from teamlimits.details import even_hex, even_hex_parse, even_hex_pattern


_T = TypeVar("T", bound="CommandPattern")


class CommandPattern:
    text: str
    _pattern: Optional[Pattern]

    @typechecked
    def __init__(self: Self, _text: str):
        self.text = _text
        self._pattern = None

    @property
    def pattern(self) -> Pattern:
        if self._pattern == None:
            self._pattern = even_hex_pattern(self.text)
        return self._pattern
    
    @typechecked
    def parse(self: Self, text: str) -> Optional["NumberedCommand"]:
        id = even_hex_parse(self.pattern, text.lstrip('/'))
        return NumberedCommand(self, id) if id is not None else None

    @classmethod
    @typechecked
    def format_number(cls: Type[_T], number: int) -> str:
        return even_hex(number)
    
    @typechecked
    def format_command(self: Self, number: int) -> str:
        return f"/{self.text}{self.format_number(number)}"
    
    @typechecked
    def make_command(self: Self, number: int) -> "NumberedCommand":
        return NumberedCommand(self, number)


class NumberedCommand:
    number: int
    pattern: CommandPattern

    def __init__(self: Self, _pattern: CommandPattern, _number: int):
        self.number = _number
        self.pattern = _pattern

    @property
    @typechecked
    def numbered_command(self: Self) -> str:
        return self.pattern.format_command(self.number)
    
    @property
    @typechecked
    def formatted_number(self: Self) -> str:
        return CommandPattern.format_number(self.number)



member_team_command = CommandPattern("member_")

manage_team_command = CommandPattern("manage_")

manage_crew_command = CommandPattern("manage_crew_")

take_a_crew_command = CommandPattern("take_a_crew_")


