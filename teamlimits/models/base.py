"""
Module models contains a set of base Models

@Author: Denis Maydykovsky
"""

from datetime import datetime
from pydantic import BaseModel, ConfigDict, NonNegativeInt, model_validator
from typing import Optional

from .common import CrewSpecial

class TeamHeader(BaseModel):
    """
    Basic information about Team: id, title, description.
    """
    id: Optional[int] = None
    title: str
    description: str = ""

    model_config = ConfigDict(from_attributes=True)


class TeamModel(TeamHeader):
    """
    Full team description.
    """
    minimalMembers: NonNegativeInt = 0
    maximalMembers: Optional[NonNegativeInt] = None
    enableCrews: bool = False
    minimalCrews: NonNegativeInt = 0
    maximalCrews: Optional[NonNegativeInt] = 0
    deadline: Optional[datetime] = None
    suspendCompanions: bool = False
    suspendRecruitment: bool = False
    suspendOnDeadline: bool = False

    model_config = ConfigDict(from_attributes=True)

    @model_validator(mode="after")
    def checkMembers(self):
        if self.maximalMembers and self.maximalMembers < self.minimalMembers:
            raise ValueError(
                f"Minimal members {self.minimalMembers} must be "
                f"less or equal than maximal members {self.maximalMembers},"
            )
        else:
            return self
        
    @model_validator(mode="after")
    def checkCrews(self):
        if self.maximalCrews and self.maximalCrews < self.minimalCrews:
            raise ValueError(
                f"Minimal crews {self.minimalCrews} must be "
                f"less or equal than maximal crews {self.maximalCrews}."
            )
        else:
            return self
    

class CrewModel(BaseModel):
    """
    A crew description.
    """

    id: Optional[int] = None
    teamId: int
    title: str
    minimalMates: NonNegativeInt = 0
    maximalMates: Optional[NonNegativeInt] = None
    position: int
    special: int

    model_config = ConfigDict(from_attributes=True)

    @model_validator(mode="after")
    def checkMates(self):
        if self.maximalMates and self.maximalMates < self.minimalMates:
            raise ValueError(
                f"Minimal mates {self.minimalMates} must be "
                f"less or equal than maximal mates {self.maximalMates}."
            )
        else:
            return self
        

    @model_validator(mode="after")
    def checkPosition(self):
        if self.special == CrewSpecial.CREW_SPECIAL_UNSET and self.position < 0:
            raise ValueError(
                f"Non-special crew {self.special} has negative position {self.position}"
            )
        else:
            return self
            

class PersonModel(BaseModel):
    """
    A basic user description.
    """
    userId: int
    userName: str
    firstName: str
    lastName: str

    model_config = ConfigDict(from_attributes=True)

    def display_user_name(self) -> str:
        """
        Build user name or id to display. 
        """
        return self.userName or str(self.userId)
    

class MemberModel(PersonModel):
    """
    Team member.
    """
    number: NonNegativeInt
    teamId: int
    crewId: Optional[int]
    position: NonNegativeInt

    model_config = ConfigDict(from_attributes=True)


class OutcastModel(PersonModel):
    """
    An Outcast (banned) person.
    """
    teamId: int

    model_config = ConfigDict(from_attributes=True)


class LeaderModel(PersonModel):
    """
    A leader for specified crew.
    A leader can not be a crew a mate or a team member.
    """
    crewId: int

    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def createFromPerson(cls, person: PersonModel, crewId: int):
        return LeaderModel(crewId=crewId, **person.model_dump())


class AdminModel(PersonModel):
    """
    A team administrator.
    An administrator can not be a team member.
    """
    teamId: int

    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def createFromPerson(cls, person: PersonModel, teamId: int):
        return AdminModel(teamId=teamId, **person.model_dump())
    

