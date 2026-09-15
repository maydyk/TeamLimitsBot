
from pydantic import ConfigDict, computed_field
from typeguard import typechecked
from typing import Self

from teamlimits.models import TeamHeader
from teamlimits.repository import CrewData, MemberData, TeamData
from teamlimits.user.tg_bot.commands import CommandPattern, manage_crew_command, manage_team_command, take_a_crew_command

class MemberView(MemberData):

    @computed_field
    @property
    @typechecked
    def userDisplay(self: Self) -> str:
        humanName = f"{self.firstName} {self.lastName}"
        numberStr = f" (+{self.number})" if self.number else ""
        if humanName.strip():
            nickName = f" @{self.userName}" if self.userName else ""
            return humanName + nickName + numberStr
        else:
            nickName = f"@{self.userName}" if self.userName else str(self.userId)
            return nickName + numberStr

    model_config = ConfigDict(from_attributes=True)


class CrewView(CrewData):
    
    @computed_field
    @property
    @typechecked
    def mateIdStr(self: Self) -> str:
        if self.is_leader:
            return manage_crew_command.make_command(self.id).numbered_command
        else:
            return CommandPattern.format_number(self.id)
        

    @computed_field
    @property
    @typechecked
    def takeACrew(self: Self) -> str:
        return take_a_crew_command.make_command(self.id).numbered_command

    model_config = ConfigDict(from_attributes=True)


class TeamHeaderView(TeamHeader):
    """
    A [TeamHeader] with additional computed field.
    We cannot use TeamHeader directly in some cases because the computed field is rejected.
    """

    def __init__(self: Self, header: TeamHeader):
        TeamHeader.__init__(self, **header.model_dump())

    
    @computed_field
    @property
    @typechecked
    def manage(self: Self) -> str:
        """
        A computed field represents id as string
        """
        return manage_team_command.make_command(self.id).numbered_command

    model_config = ConfigDict(from_attributes=True)


class TeamView(TeamData):
    
    @computed_field
    @property
    def memberIdStr(self: Self) -> str:
        """
        Format id as admin
        """
        if self.is_admin:
            return manage_team_command.make_command(self.id).numbered_command
        else:
            return CommandPattern.format_number(self.id)
    

    model_config = ConfigDict(from_attributes=True)
