"""
module domain

An intermediate layer between database.Repository() and Telegram UI
@Author: Denis Maydykovsky
"""

import logging

from contextlib import asynccontextmanager
from functools import wraps
from itertools import chain
from typing import Any, Awaitable, Callable, List, Optional

from teamlimits.database.database import Database, DatabaseError
from teamlimits.details.coerce_list import coerce_first
from teamlimits.details.list_difference import list_difference, list_intersection
from teamlimits.details.singleton import Singleton

from teamlimits.models.fields import fields
from teamlimits.models.base import AdminModel, CrewModel, OutcastModel, PersonModel, MemberModel, TeamHeader, TeamModel
from teamlimits.models.common import CrewSpecial
from teamlimits.database.models_data import MemberData, TeamData
from teamlimits.repository.models_view import CrewView, MemberView, TeamView

_logger = logging.getLogger(__name__)


class RepositoryError(Exception):
    pass


def database_error(method: Callable[..., Awaitable[Any]]) -> Callable[..., Awaitable[Any]]:
    """
    Decorator to translate 'DatabaseError' to 'RepositoryError'
    """
    @wraps(method)
    async def wrapper(self, *args, **kwargs) -> Any:
        try:
            return await method(self, *args, **kwargs)
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
    async def checkTeamTitleIsUnique(self, title) -> bool:
        return await self.database.checkTeamTitleIsUnique(title=title)
    

    @database_error
    async def insertTeam(self, person: PersonModel, team: TeamModel) -> int:
        return await self.database.insertTeam(person=person, teamModel=team)
    

    @database_error
    async def updateTeam(self, person: PersonModel, team: TeamModel) -> int:
        return await self.database.updateTeam(person=person, teamModel=team)
    

    @database_error
    async def deleteTeam(self, admin: PersonModel, teamId: int) -> None:    
        await self.database.deleteTeam(admin = admin, teamId=teamId)


    @database_error
    async def queryAdminTeam(self, admin: PersonModel, teamId: int) -> TeamModel:
        return await self.database.queryAdminTeam(admin=admin, teamId=teamId)


    @database_error
    async def queryAdminTeamHeaders(self, admin: PersonModel) -> List[TeamHeader]:
        return await self.database.queryAdminTeamHeaders(admin=admin)
    

    @database_error
    async def checkAdminTeam(self, admin: AdminModel) -> bool:
        return await self.database.checkAdminTeam(admin)

    
    @database_error
    async def checkOutcastMember(self, outcast: OutcastModel) -> bool:
        return await self.database.checkOutcastMember(outcast)
    
    
    @database_error
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
            as_admin=teamData.as_admin,
            as_member=teamData.as_member,
            activeCrews=activeCrews,
            queuedCrews=queuedCrews,
            defaultCrew=CrewView.model_validate(defaultCrew.model_dump()),
            activeOutboards=make_member_view_list(activeOutboards),
            queuedOutboards=make_member_view_list(queuedOutboards),
            **TeamModel.model_validate(teamData.model_dump()).model_dump()
        )

    
    @database_error
    async def canAddTeamMember(self, member: MemberModel) -> bool:
        return await self.database.canAddTeamMember(member)
    
    @database_error
    async def addTeamMember(self, member: MemberModel, crewId: Optional[int]) -> None:
        await self.database.addTeamMember(member = member, crewId=crewId)

    
    @database_error
    async def removeTeamMember(self, member: MemberModel) -> None:
        await self.database.removeTeamMember(member)


    @database_error
    async def checkCrewTitleIsUnique(self, teamId: int, title: str) -> bool:
        return await self.database.checkCrewTitleIsUnique(teamId = teamId, title = title)


    @database_error
    async def insertCrew(self, person: PersonModel, crew: CrewModel) -> int:
        return await self.database.insertCrew(personModel = person, crewModel = crew)


    @database_error
    async def updateCrew(self, leader: PersonModel, crew: CrewModel) -> int:
        return await self.database.updateCrew(leader = leader, crew = crew)


    @database_error
    async def deleteCrew(self, leader: PersonModel, crewId: int) -> None:
        await self.database.deleteCrew(leader = leader, crewId=crewId)


    @database_error
    async def queryMemberTeams(self, member: PersonModel) -> List[TeamModel]:
        return await self.database.queryMemberTeams(member = member)
    
    
    @database_error
    async def setCrewMate(self, mate: MemberModel, crewId: int, ) -> None:
        return await self.database.setCrewMate(mate=mate, crewId=crewId)
    

    @database_error
    async def queryLeaderCrew(self, leader: PersonModel, crewId: int, ) -> CrewModel:
        return await self.database.queryLeaderCrew(leader=leader, crewId = crewId)
