"""
Module models

@Author: Denis Maydykovsky
"""

from dataclasses import dataclass
from datetime import datetime
from functools import lru_cache
from pydantic import BaseModel, ConfigDict, Field, NonNegativeInt, StringConstraints, model_validator
from typing import TypeVar, cast, Any, reveal_type, TYPE_CHECKING
from typing import List, Optional

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
        if self.maximalMates > self.minimalMates:
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


class AdminModel(PersonModel):
    teamId: int

    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def createFromPerson(cls, person: PersonModel, teamId: int):
        return AdminModel(teamId=teamId, **person.model_dump())
    

class CrewSummary(BaseModel):
    as_leader: bool
    crew: CrewModel
    mates: List[MemberModel]

    model_config = ConfigDict(from_attributes=True)


class TeamSummary(BaseModel):
    as_member: bool
    as_admin: bool
    team: TeamModel
    members: List[MemberModel]
    crews: List[CrewSummary]

    model_config = ConfigDict(from_attributes=True)



# Get names of models fields
# See https://github.com/pydantic/pydantic/discussions/8600#discussioncomment-8212526

@dataclass(frozen=True)
class _GetFields:
    _model: type[BaseModel]

    def __getattr__(self, item: str) -> Any:
        if item in self._model.model_fields:
            return item

        return getattr(self._model, item)


TModel = TypeVar("TModel", bound=BaseModel)


def fields(model: type[TModel], /) -> TModel:
    return cast(TModel, _GetFields(model))


if not TYPE_CHECKING:
    fields = lru_cache(maxsize=256)(fields)



