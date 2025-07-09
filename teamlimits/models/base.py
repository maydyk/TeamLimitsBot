"""
Module models contains a set of base Models

@Author: Denis Maydykovsky
"""

from datetime import datetime
from pydantic import BaseModel, ConfigDict, NonNegativeInt, model_validator
from typing import Any, Optional, Type, TypeVar

from teamlimits.details import even_hex
from teamlimits.models import CrewSpecial, fields

class TeamHeader(BaseModel):
    """
    Basic information about Team: id, title, description.
    """
    id: Optional[int] = None
    title: str
    description: str = ""

    model_config = ConfigDict(from_attributes=True)

    def teamIdStr(self) -> str:
        """
        Present team is as even hex string.
        """
        return even_hex(id)


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

    def isDefaultCrew(self) -> bool:
        return self.special == CrewSpecial.CREW_SPECIAL_DEFAULT
    

    def isRegularCrew(self) -> bool:
        return self.special == CrewSpecial.CREW_SPECIAL_UNSET


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
        if self.isRegularCrew() and self.position < 0:
            raise ValueError(
                f"Non-special crew {self.special} has negative position {self.position}"
            )
        else:
            return self
            
    
_TPerson = TypeVar("TPerson")

def _find_id_field(modelType: Type[_TPerson]) -> str:
    match modelType:
        case t if t is MemberModel:
            field = fields(MemberModel).teamId

        case t if t is OutcastModel:
            field = fields(OutcastModel).teamId

        case t if t is AdminModel:
            field = fields(AdminModel).teamId

        case t if t is LeaderModel:
            field = fields(LeaderModel).crewId
        
        case _:
            assert False, f"Unknown Model class: {modelType}."
    
    return field


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
    

    def combineId(self, modelType: Type[_TPerson], id: int, field: str = None) -> _TPerson:
        # Smart select field name
        if field is None:
            field = _find_id_field(modelType)

        return modelType(**(self.model_dump() | { field: id }))


class MemberModel(PersonModel):
    """
    A member: a PersonModel with team id
    """
    teamId: int

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


class AdminModel(PersonModel):
    """
    A team administrator.
    An administrator can not be a team member.
    """
    teamId: int

    model_config = ConfigDict(from_attributes=True)
    


class TeamMember(MemberModel):
    """
    A team member.
    """
    number: NonNegativeInt
    crewId: Optional[int]
    position: NonNegativeInt

    model_config = ConfigDict(from_attributes=True)




