"""
Module models

@Author: Denis Maydykovsky
"""

from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field, NonNegativeInt, StringConstraints, model_validator
from model_fields import fields
from typing import Any, Dict, List, Optional, Tuple

class TeamHeader(BaseModel):
    id: Optional[int] = None
    title: str
    description: str = ""

    model_config = ConfigDict(from_attributes=True)


class TeamModel(TeamHeader):
    minimalMembers: NonNegativeInt = 0
    maximalMembers: NonNegativeInt = 0
    enableCrews: bool = False
    minimalCrews: NonNegativeInt = 0
    maximalCrews: NonNegativeInt = 0
    deadline: Optional[datetime] = None
    suspendCompanions: bool = False
    suspendRecruitment: bool = False
    suspendPendingQueue: bool = False
    suspendDeadlineQueue: bool = False

    model_config = ConfigDict(from_attributes=True)

    @model_validator(mode="after")
    def checkMembers(self):
        if self.maximalMembers < self.minimalMembers:
            raise ValueError(
                f"Minimal members {self.minimalMembers} must be "
                f"less or equal than maximal members {self.maximalMembers},"
            )
        else:
            return self
        
    @model_validator(mode="after")
    def checkCrews(self):
        if self.maximalCrews < self.minimalCrews:
            raise ValueError(
                f"Minimal crews {self.minimalCrews} must be "
                f"less or equal than maximal crews {self.maximalCrews}."
            )
        else:
            return self
    

class CrewModel(BaseModel):
    id: Optional[int] = None
    teamId: int
    title: str
    minimalMates: NonNegativeInt = 0
    maximalMates: NonNegativeInt = 0
    special: int = 0

    model_config = ConfigDict(from_attributes=True)

    @model_validator(mode="after")
    def checkMates(self):
        if self.maximalMates < self.minimalMates:
            raise ValueError(
                f"Minimal mates {self.minimalMates} must be "
                f"less or equal than maximal mates {self.maximalMates}."
            )
        else:
            return self
            

class PersonModel(BaseModel):
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
    number: NonNegativeInt
    teamId: int
    crewId: Optional[int]
    position: NonNegativeInt

    model_config = ConfigDict(from_attributes=True)


class OutcastModel(PersonModel):
    teamId: int

    model_config = ConfigDict(from_attributes=True)


class LeaderModel(PersonModel):
    crewId: int

    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def createFromPerson(cls, person: PersonModel, crewId: int):
        return LeaderModel(crewId=crewId, **person.model_dump())


class AdminModel(PersonModel):
    teamId: int

    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def createFromPerson(cls, person: PersonModel, teamId: int):
        return AdminModel(teamId=teamId, **person.model_dump())
    

class CrewSummary(CrewModel):
    crewIdStr: str
    as_leader: bool
    mates: List[MemberModel]

    model_config = ConfigDict(from_attributes=True)


class TeamSummary(TeamModel):
    teamIdStr: str
    as_member: bool
    as_admin: bool
    crews: List[CrewSummary]
    defaultCrew: CrewSummary
    members: List[MemberModel]
    totalMembers: int
    deadlineDaysLeft: Optional[int]
    canAddMember: bool
    canRemoveMember: bool
    canAddMemberCrew: bool

    model_config = ConfigDict(from_attributes=True)







