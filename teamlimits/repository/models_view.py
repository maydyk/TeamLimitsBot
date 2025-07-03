
from pydantic import ConfigDict, computed_field
from typing import List, Optional
from datetime import datetime
from functools import reduce

from ..models.base import CrewModel, MemberModel, TeamHeader, TeamModel
from ..details.even_hex import even_hex

class MemberView(MemberModel):

    @computed_field
    @property
    def userStrId(self) -> str:
        if self.userName:
            nameStr = self.userName
        else:
            nameStr = str(self.userId)
        
        if self.number:
            nameStr = nameStr + f" (+{self.number})"
        
        return nameStr

    model_config = ConfigDict(from_attributes=True)


class CrewView(CrewModel):

    @computed_field
    @property
    def idStr(self) -> str:
        """
        A computed field represents id as string
        """
        return even_hex(self.id)
    
    @computed_field
    @property
    def mateIdStr(self) -> str:
        if self.as_leader:
            return f"/mc{self.idStr}"
        else:
            return self.idStr

    as_leader: bool
    activeMates: List[MemberView]
    queuedMates: List[MemberView]

    model_config = ConfigDict(from_attributes=True)


class TeamHeaderView(TeamHeader):
    """
    A [TeamHeader] with additional computed field.
    We cannot use TeamHeader directly in some cases because the computed field is rejected.
    """

    def __init__(self, header: TeamHeader):
        TeamHeader.__init__(self, **header.model_dump())

    
    @computed_field
    @property
    def idStr(self) -> str:
        """
        A computed field represents id as string
        """
        return even_hex(self.id)


    model_config = ConfigDict(from_attributes=True)



class TeamView(TeamModel):
    as_member: bool
    as_admin: bool
    activeCrews: List[CrewView]
    queuedCrews: List[CrewView]
    defaultCrew: CrewView
    outboards: List[MemberView]

    @computed_field
    @property
    def idStr(self) -> str:
        """
        Format is as hex.
        """
        return even_hex(self.id)
    
    @computed_field
    @property
    def memberIdStr(self) -> str:
        """
        Format id as admin
        """
        if self.as_admin:
            return f"/m{self.idStr}"
        else:
            return self.idStr
    

    @staticmethod
    def compute_total_mates(crews: List[CrewView]) -> int:
        return reduce(
            lambda sum, crew: sum + len(crew.activeMates) + len(crew.queuedMates),
            crews,
            0,
        )
    

    _totalMembers: Optional[int] = None

    @computed_field
    @property
    def totalMembers(self) -> int:
        if self._totalMembers is None:
            self._totalMembers = len(self.outboards) 
            + TeamView.compute_total_mates(self.activeCrews) 
            + TeamView.compute_total_mates(self.queuedCrews)
        return self._totalMembers
                
            
    @computed_field
    @property
    def membersLeft(self) -> int:
        max(0, self.minimalMembers - self.totalMembers)


    @computed_field
    @property
    def teamIsFull(self) -> bool:
        return self.maximalMembers == None or self.totalMembers <= self.maximalMembers
            

    @computed_field
    @property
    def deadlineDaysLeft(self) -> Optional[int]:
        return (self.deadline - datetime.now()).days if self.deadline is not None else None
    

    @computed_field
    @property
    def canAddMember(self) -> bool:
        return not (self.suspendCompanions and self.as_member)
    
    @computed_field
    @property
    def canRemoveMember(self) -> bool:
        return self.as_member
    

    @computed_field
    @property
    def canAddMemberCrew(self) -> bool:
        return self.enableCrews or self.as_admin
    
    @computed_field
    @property
    def hasCrews(self) -> bool:
        return len(self.activeCrews) + len(self.queuedCrews) > 0
    
    
    model_config = ConfigDict(from_attributes=True)

