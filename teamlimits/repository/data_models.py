"""
Rearranged data given from database
"""
from abc import ABC, abstractmethod
from pydantic import ConfigDict, computed_field
from typing import Any, Dict, Generic, List, Optional, Self, TypeVar


from teamlimits.models import CrewModel, TeamMember, TeamModel

class MemberData(TeamMember):
    model_config = ConfigDict(from_attributes=True)


MemberType = TypeVar("MemberData", bound=MemberData)


class CrewData(CrewModel):
    is_admin: bool
    is_leader: bool
    mates: List[MemberType] # All mates, including active and queued
    activeMates: List[MemberType]
    queuedMates: List[MemberType]

    model_config = ConfigDict(from_attributes=True)


CrewType = TypeVar("CrewType", bound=CrewData)


# Raw team data from database
class TeamData(TeamModel, Generic[MemberType, CrewType]):
    is_admin: bool
    is_member: bool
    can_insert_member: bool
    can_remove_member: bool
    can_insert_crew: bool
    can_remove_crew: bool
    deadline_days_left: Optional[int]
    members: List[MemberType] # All members, including crew mates and outboards
    crews: List[CrewType] # All crews, including active, queued and default
    activeCrews: List[CrewType]
    queuedCrews: List[CrewType]
    defaultCrew: CrewType
    activeOutboards: List[MemberType]
    queuedOutboards: List[MemberType]
                            
    @computed_field
    @property
    def membersLeft(self) -> int:
        max(0, self.minimalMembers - self.totalMembers)


    @computed_field
    @property
    def teamIsStuffed(self) -> bool:
        return self.maximalMembers == None or self.totalMembers <= self.maximalMembers
                    
    
    @computed_field
    @property
    def hasActiveCrews(self) -> bool:
        return bool(self.activeCrews)
    

    @computed_field
    @property
    def hasQueuedCrews(self) -> bool:
        return bool(self.queuedCrews) 
    
    
    @computed_field
    @property
    def hasActiveMembers(self) -> bool:
        return bool(self.activeOutboards)
    

    @computed_field
    @property
    def hasQueuedMembers(self) -> bool:
        return bool(self.queuedOutboards)
    

    @computed_field
    @property
    def hasDefaultMates(self) -> bool:
        return bool(self.defaultCrew.mates)


    model_config = ConfigDict(from_attributes=True)


TeamType = TypeVar("TeamType", bound=TeamData)

AdapterType = Generic[MemberType, CrewType, TeamType]

class TypeAdapter(ABC, AdapterType):

    @abstractmethod
    def make_member(self: Self, data: Dict[str, Any]) -> MemberType:
        pass

    @abstractmethod
    def make_crew(self: Self, data: Dict[str, Any]) -> CrewType:
        pass

    @abstractmethod
    def make_team(self: Self, data: Dict[str, Any]) -> TeamType:
        pass
