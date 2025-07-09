"""
Rearranged data given from database
"""

from pydantic import ConfigDict, computed_field
from typing import List, Optional


from teamlimits.details import coerce_first, coerce_last
from teamlimits.models import CrewModel, TeamMember, TeamModel

class MemberData(TeamMember, frozen=True):
    model_config = ConfigDict(from_attributes=True)


class CrewData(CrewModel):
    is_admin: bool
    is_leader: bool
    mates: List[MemberData]

    # Cache computed fields
    _activeMates: Optional[List[MemberData]] = None
    _queuedMates: Optional[List[MemberData]] = None

    
    @computed_field
    @property
    def activeMates(self) -> List[MemberData]:
        """
        Mates who can drive with this Crew.
        """
        if self._activeMates is None:
            self._activeMates = coerce_first(self.mates, self.maximalMates)
        return self._activeMates
    

    @computed_field
    @property
    def queuedMates(self) -> List[MemberData]:
        """
        Mates queued with this Crew.
        """
        if self._queuedMates is None:
            self._queuedMates = coerce_last(self.mates, self.maximalMates)
        return self._queuedMates
    

    def acceptMates(self, defaultMates: List[MemberData]) -> List[MemberData]:
        """
        Move mates from the specified list [defaultMates] to our [mates]
        """
        while len(defaultMates) and (self.maximalMates is None or len(self.mates) <= self.maximalMates):
            mate = defaultMates[0]
            self.mates.append(mate)
            defaultMates = defaultMates[1:] 
        
        # Reset cache
        self._activeMates = None
        self._queuedMates = None
        return defaultMates

    model_config = ConfigDict(from_attributes=True)


# Raw team data from database
class TeamData(TeamModel):
    is_admin: bool
    is_member: bool
    can_insert_member: bool
    can_remove_member: bool
    can_insert_crew: bool
    deadline_days_left: Optional[int]
    crews: List[CrewData]
    outboards: List[MemberData]

    # Cache computed fields
    _defaultCrew: Optional[CrewData] = None
    _regularCrews: Optional[List[CrewData]] = None
    _activeCrews: Optional[List[CrewData]] = None
    _queuedCrews: Optional[List[CrewData]] = None

    @computed_field
    @property
    def defaultCrew(self) -> CrewData:
        """
        Extract default crew from [crews]
        """
        if self._defaultCrew is None:
            self._defaultCrew = next(
                filter(
                    lambda crew: crew.isDefaultCrew(),
                    self.crews
                    )
                )
        return self._defaultCrew
    

    @computed_field
    @property
    def regularCrews(self) -> List[CrewData]:
        """
        All crews except default.
        """
        if self._regularCrews is None:
            self._regularCrews = list(
                filter(
                    lambda crew: crew.isRegularCrew(),
                    self.crews
                    )
            )
        return self._regularCrews
    
    
    @computed_field
    @property
    def activeCrews(self) -> List[CrewData]:
        """
        Crews can participate in the Team 
        """
        if self._activeCrews is None:
            self._activeCrews = coerce_first(self.regularCrews, self.maximalCrews)
        return self._activeCrews
    

    @computed_field
    @property
    def queuedCrews(self) -> List[CrewData]:
        """
        Crews out of the limit
        """
        if self._queuedCrews is None:
            self._queuedCrews = coerce_last(self.regularCrews, self.maximalCrews)
        return self._queuedCrews


    model_config = ConfigDict(from_attributes=True)

