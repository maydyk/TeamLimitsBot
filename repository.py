"""
module domain

An intermediate layer between database.Repository() and Telegram UI
@Author: Denis Maydykovsky
"""

from aiogram.types import User
from contextlib import asynccontextmanager
from database import Database, DatabaseError
from details import coerce_first, list_difference, Singleton
from functools import wraps
from itertools import chain
from model_fields import fields
from typing import Any, Awaitable, Callable, Dict, List, Optional, Tuple
from models_base import CrewModel, PersonModel, MemberModel, TeamHeader, TeamModel
from models_data import CrewData, MemberData, TeamData
from models_view import CrewView, MemberView, TeamView

import logging

_logger = logging.getLogger(__name__)

def make_person(user: User) -> PersonModel:
    return PersonModel(
        userId=user.id,
        userName=user.username,
        firstName=user.first_name,
        lastName=user.last_name,
    )


def make_person_team(data: Dict[str, Any]) -> Tuple[int, PersonModel]:
    """
    Extracts team id and person data from specifies dictionary.
    """
    teamId = data[fields(MemberModel).teamId]
    person = PersonModel(**data)
    return (teamId, person)


def get_person_team(teamId: int, person: PersonModel) -> Dict[str, Any]:
    """
    Combine person with teamId
    """
    return dict(
        person.model_dump(),
        **{ fields(MemberModel).teamId : teamId }
        )


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
            yield
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
        return await self.database.insertTeam(personModel=person, teamModel=team)
    

    @database_error
    async def updateTeam(self, team: TeamModel) -> int:
        return await self.database.updateTeam(teamModel=team)
    

    @database_error
    async def deleteTeam(self, teamId: int) -> None:    
        await self.database.deleteTeam(teamId=teamId)


    @database_error
    async def queryAdminTeam(self, teamId: int, admin: PersonModel) -> TeamModel:
        return await self.database.queryAdminTeam(teamId=teamId, adminModel=admin)


    @database_error
    async def queryAdminTeamHeaders(self, admin: PersonModel) -> List[TeamHeader]:
        return await self.database.queryAdminTeamHeaders(adminModel=admin)
    

    @database_error
    async def checkAdminTeam(self, teamId: int, admin: PersonModel) -> bool:
        return await self.database.checkAdminTeam(teamId = teamId, adminModel = admin)

    
    @database_error
    async def checkOutcastMember(self, teamId: int, member: PersonModel) -> bool:
        return await self.database.checkOutcastMember(teamId=teamId, memberModel=member)
    
    
    @database_error
    async def queryTeamView(self, teamId: int, member: PersonModel) -> TeamView:
        # Query all team data
        teamData: TeamData = await self.database.queryTeamData(teamId=teamId, memberModel=member)

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
                lambda member: member.crewId == CrewData._CREW_SPECIAL_DEFAULT,
                validMembers
            )
        )

        # Distribute default mates per free places in the crews
        for crew in teamData.activeCrews:
            validDefaultCrewMembers = crew.acceptMates(validDefaultCrewMembers)

        # Update default crew members
        teamData.defaultCrew.mates  = list_difference(teamData.defaultCrew.mates, validDefaultCrewMembers)

        # Update outboards
        teamData.outboards = list_difference(teamData.outboards, validMembers)

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
            ))

        
        # Build TeamSummary
        return TeamView.model_validate(
            teamData.model_dump() |
            {
                fields(TeamView).as_admin : teamData.as_admin,
                fields(TeamView).as_member : teamData.as_member,
                fields(TeamView).activeCrews : activeCrews,
                fields(TeamView).queuedCrews : queuedCrews,
                fields(TeamView).defaultCrew : CrewView.model_validate(defaultCrew.model_dump()),
                fields(TeamView).outboards : make_member_view_list(teamData.outboards),
            }
        )

    
    @database_error
    async def canAddTeamMember(self, teamId: int, member: PersonModel) -> bool:
        return await self.database.canAddTeamMember(teamId = teamId, memberModel = member)
    
    @database_error
    async def addTeamMember(self, teamId: int, crewId: Optional[int], member: PersonModel) -> None:
        await self.database.addTeamMember(teamId = teamId, crewId=crewId, memberModel = member)

    
    @database_error
    async def removeTeamMember(self, teamId: int, member: PersonModel) -> None:
        await self.database.removeTeamMember(teamId = teamId, memberModel = member)


    @database_error
    async def checkCrewTitleIsUnique(self, teamId: int, title: str) -> bool:
        return await self.database.checkCrewTitleIsUnique(teamId = teamId, title = title)


    @database_error
    async def insertCrew(self, person: PersonModel, crew: CrewModel) -> int:
        return await self.database.insertCrew(personModel = person, crewModel = crew)


    @database_error
    async def updateCrew(self, crew: CrewModel) -> int:
        return await self.database.updateCrew(crewModel = crew)


    @database_error
    async def deleteCrew(self, crewId: int) -> None:
        await self.database.deleteCrew(crewId=crewId)


    @database_error
    async def queryMemberTeams(self, member: PersonModel) -> List[TeamModel]:
        return await self.database.queryMemberTeams(memberModel = member)
    
    
    @database_error
    async def setCrewMate(self, teamId: int, crewId: int, mate: PersonModel) -> None:
        return await self.database.setCrewMate(teamId=teamId, crewId=crewId, mateModel=mate)
    

    @database_error
    async def queryLeaderCrew(self, crewId: int, person: PersonModel) -> CrewModel:
        return await self.database.queryLeaderCrew(crewId = crewId, personModel=person)
