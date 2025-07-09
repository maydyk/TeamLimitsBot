
from datetime import datetime
from itertools import chain
from functools import reduce
from pydantic import ConfigDict, computed_field
from typeguard import typechecked
from typing import List, Optional

from teamlimits.models import CrewModel, CrewSpecial, TeamHeader, TeamMember, TeamModel, TeamData, MemberData
from teamlimits.details import coerce_first, even_hex, list_difference, list_intersection

class MemberView(TeamMember):

    @computed_field
    @property
    def userDisplay(self) -> str:
        humanName = f"{self.firstName} {self.lastName}"
        numberStr = f" (+{self.number})" if self.number else ""
        if humanName.strip():
            nickName = f" @{self.userName}" if self.userName else ""
            return humanName + nickName + numberStr
        else:
            nickName = f"@{self.userName}" if self.userName else str(self.userId)
            return nickName + numberStr

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
        if self.is_leader:
            return f"/mc{self.idStr}"
        else:
            return self.idStr

    is_leader: bool
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
    is_member: bool
    is_admin: bool
    can_insert_member: bool
    can_remove_member: bool
    can_insert_crew: bool
    deadline_days_left: Optional[int]
    activeCrews: List[CrewView]
    queuedCrews: List[CrewView]
    defaultCrew: CrewView
    activeOutboards: List[MemberView]
    queuedOutboards: List[MemberView]

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
        if self.is_admin:
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
            self._totalMembers = \
                len(self.activeOutboards) + \
                len(self.queuedOutboards) + \
                TeamView.compute_total_mates(self.activeCrews) + \
                TeamView.compute_total_mates(self.queuedCrews)
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
    def hasDefaultCrew(self) -> bool:
        return bool(self.defaultCrew.activeMates)


    model_config = ConfigDict(from_attributes=True)

@typechecked
def make_team_view(teamData: TeamData) -> TeamView:
    """
    Build a view for the given team data.
    """
    defaultCrew = teamData.defaultCrew

    # Build member list: sorted by position of outboards and crew mates
    # and attached default crew members
    totalMembers = sorted(
        chain(
            teamData.outboards, 
            chain.from_iterable([crew.activeMates for crew in teamData.activeCrews]),
        ),
        key = lambda member: member.position
    ) + defaultCrew.mates

    # Get first maximal members
    validMembers = coerce_first(totalMembers, teamData.maximalMembers)

    # Extract default crew members from valid list.
    validDefaultCrewMembers = list(
        filter(
            lambda member: member.crewId == CrewSpecial.CREW_SPECIAL_DEFAULT,
            validMembers
        )
    )

    # Distribute default mates per free places in the crews
    for crew in teamData.activeCrews:
        validDefaultCrewMembers = crew.acceptMates(validDefaultCrewMembers)

    # Update default crew members
    teamData.defaultCrew.mates = list_difference(teamData.defaultCrew.mates, validDefaultCrewMembers)

    # Update outboards
    activeOutboards = list_intersection(teamData.outboards, validMembers)
    queuedOutboards = list_difference(teamData.outboards, validMembers)

    # Transform CrewData to CrewView
    activeCrews = list(
        map(
            lambda crewData: CrewView.model_validate(crewData.model_dump()),
            teamData.activeCrews
        )
    )

    queuedCrews = list(
        map(
            lambda crewData: CrewView.model_validate(crewData.model_dump()),
            teamData.queuedCrews
        )
    )

    def make_member_view_list(memberDataList: List[MemberData]) -> List[MemberView]:
        return list(map(
            lambda memberData: MemberView.model_validate(memberData.model_dump()),
            memberDataList
            )
        )
    
    # Build TeamSummary
    return TeamView(
        is_admin=teamData.is_admin,
        is_member=teamData.is_member,
        can_insert_member=teamData.can_insert_member,
        can_remove_member=teamData.can_remove_member,
        can_insert_crew=teamData.can_insert_crew,
        deadline_days_left=teamData.deadline_days_left,
        activeCrews=activeCrews,
        queuedCrews=queuedCrews,
        defaultCrew=CrewView.model_validate(defaultCrew.model_dump()),
        activeOutboards=make_member_view_list(activeOutboards),
        queuedOutboards=make_member_view_list(queuedOutboards),
        **TeamModel.model_validate(teamData.model_dump()).model_dump()
    )