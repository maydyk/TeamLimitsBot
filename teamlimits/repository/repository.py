"""
module domain

An intermediate layer between database.Repository() and Telegram UI
@Author: Denis Maydykovsky
"""

import logging

from contextlib import asynccontextmanager
from datetime import datetime
from functools import wraps
from itertools import chain
from typeguard import typechecked
from typing import Awaitable, Callable, List, Optional, TypeVar, Union

from teamlimits.database.database import Database, DatabaseError, DatabasePermissionError
from teamlimits.details.coerce_list import coerce_first
from teamlimits.details.list_difference import list_difference, list_intersection
from teamlimits.details.singleton import Singleton

from teamlimits.models.fields import fields
from teamlimits.models.base import AdminModel, CrewModel, LeaderModel, PersonModel, MemberModel, TeamHeader, TeamModel
from teamlimits.models.common import CrewSpecial
from teamlimits.database.models_data import MemberData, TeamData
from teamlimits.repository.models_view import CrewView, MemberView, TeamView

_logger = logging.getLogger(__name__)


class RepositoryError(Exception):
    pass

class RepositoryPermissionError(RepositoryError):
    pass


_T = TypeVar("T")

def database_error(method: Callable[..., Awaitable[_T]]) -> Callable[..., Awaitable[_T]]:
    """
    Decorator to translate 'DatabaseError' to 'RepositoryError'
    """
    @wraps(method)
    async def wrapper(self, *args, **kwargs) -> _T:
        try:
            return await method(self, *args, **kwargs)
        except DatabasePermissionError as db_permission_error:
            # Translate Permission error
            breakpoint()
            raise RepositoryPermissionError(*db_permission_error.args)
        except DatabaseError as db_error:
            breakpoint()
            raise RepositoryError(*db_error.args)
                
    return wrapper


class Repository(metaclass = Singleton):

    database: Database

    @classmethod
    def create(cls, databaseUrl: str):
        # Create an instance
        self = cls()

        self.database = Database(databaseUrl)
        return self
    

    async def close(self):
        await self.database.close()
    

    @classmethod
    @asynccontextmanager
    async def build(cls: type, database: str):
        """
        A context manager for the Repository
        """
        repository = cls.create(database)
        try:
            yield repository
        except Exception as ex:
            _logger.exception("A SQL exception", ex)
            raise
        finally:
            await repository.close()
    

    @database_error
    @typechecked
    async def checkTeamTitleIsUnique(self, title) -> bool:
        return await self.database.checkTeamTitleIsUnique(title=title)
    

    @database_error
    @typechecked
    async def insertTeam(self, person: PersonModel, team: TeamModel) -> int:
        return await self.database.insertTeam(person=person, team=team)
    

    @database_error
    @typechecked
    async def updateTeam(self, admin: AdminModel, team: TeamModel) -> int:
        return await self.database.updateTeam(admin=admin, team=team)
    

    @database_error
    @typechecked
    async def deleteTeam(self, admin: AdminModel) -> None:
        await self.database.deleteTeam(admin = admin)


    @database_error
    @typechecked
    async def queryAdminTeam(self, admin: AdminModel, teamId: int) -> TeamModel:
        return await self.database.queryAdminTeam(admin=admin, teamId=teamId)


    @database_error
    @typechecked
    async def queryAdminTeamHeaders(self, person: PersonModel) -> List[TeamHeader]:
        return await self.database.queryAdminTeamHeaders(person)
    
    
    @database_error
    @typechecked
    async def queryMemberTeamHeaders(self, person: PersonModel) -> List[TeamHeader]:
        return await self.database.queryMemberTeamHeaders(member = member)
    

    @database_error
    @typechecked
    async def canViewTeam(self, member: MemberModel) -> bool:
        return await self.database.canViewTeam(member)
    
    
    @database_error
    @typechecked
    async def queryTeamView(self, member: MemberModel) -> TeamView:
        # Query all team data
        teamData: TeamData = await self.database.queryTeamData(member)

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
            activeCrews=activeCrews,
            queuedCrews=queuedCrews,
            defaultCrew=CrewView.model_validate(defaultCrew.model_dump()),
            activeOutboards=make_member_view_list(activeOutboards),
            queuedOutboards=make_member_view_list(queuedOutboards),
            **TeamModel.model_validate(teamData.model_dump()).model_dump()
        )

    
    @database_error
    @typechecked
    async def canAddTeamMember(self, member: MemberModel, date: datetime) -> bool:
        return await self.database.canAddTeamMember(member, date)
    
    @database_error
    @typechecked
    async def addTeamMember(self, member: MemberModel, crewId: Optional[int], date: datetime) -> None:
        await self.database.addTeamMember(member, crewId, date)


    @database_error
    @typechecked
    async def canRemoveTeamMember(self, member: MemberModel, date: datetime) -> bool:
        return await self.database.canRemoveTeamMember(member, date)
    

    @database_error
    @typechecked
    async def removeTeamMember(self, member: MemberModel, date: datetime) -> None:
        await self.database.removeTeamMember(member, date)


    @database_error
    @typechecked
    async def checkCrewTitleIsUnique(self, teamId: int, title: str) -> bool:
        return await self.database.checkCrewTitleIsUnique(teamId = teamId, title = title)


    @database_error
    @typechecked
    async def canInsertCrew(self, person: Union[MemberModel, AdminModel], date: datetime) -> bool:
        return await self.database.canInsertCrew(person, date)


    @database_error
    @typechecked
    async def insertCrew(self, person: Union[MemberModel, AdminModel], crew: CrewModel, date: datetime) -> int:
        return await self.database.insertCrew(person, crew, date)


    @database_error
    @typechecked
    async def canUpdateCrew(self, leader: Union[LeaderModel, AdminModel], date: datetime) -> bool:
        return await self.database.canUpdateCrew(leader, date)
    
    
    @database_error
    @typechecked
    async def updateCrew(self, leader: Union[LeaderModel, AdminModel], crew: CrewModel, date: datetime) -> int:
        return await self.database.updateCrew(leader, crew, date)


    @database_error
    @typechecked
    async def canDeleteCrew(self, leader: Union[LeaderModel, AdminModel], date: datetime) -> bool:
        return await self.database.canDeleteCrew(leader, date)


    @database_error
    @typechecked
    async def deleteCrew(self, leader: Union[MemberModel, AdminModel], crewId: int, date: datetime) -> None:
        await self.database.deleteCrew(leader, crewId, date)

    
    @database_error
    @typechecked
    async def setCrewMate(self, mate: MemberModel, crewId: int, ) -> None:
        return await self.database.setCrewMate(mate=mate, crewId=crewId)
    

    @database_error
    @typechecked
    async def queryLeaderCrew(self, leader: PersonModel, crewId: int, ) -> CrewModel:
        return await self.database.queryLeaderCrew(leader=leader, crewId = crewId)
