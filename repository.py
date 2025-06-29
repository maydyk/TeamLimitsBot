"""
module domain

An intermediate layer between database.Repository() and Telegram UI
@Author: Denis Maydykovsky
"""

from aiogram.types import User
from collections import deque
from contextlib import asynccontextmanager
from database import CrewInfo, Database, DatabaseError, TeamInfo
from details import even_hex, Singleton
from functools import wraps
from itertools import accumulate
from models import *
from model_fields import fields
from typing import Any, Awaitable, Callable, Dict, Tuple

import datetime
import logging

_logger = logging.getLogger(__name__)

def make_person(user: User) -> PersonModel:
    return PersonModel(
        userId=user.id,
        userName=user.username,
        firstName=user.first_name,
        lastName=user.last_name,
    )


def make_person_team(data: Dict[str, Any]) -> Tuple[int, Any]:
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
        **{ fields(MemberModel).teamId : teamId}
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


    async def checkTeamTitleIsUnique(self, title) -> bool:
        return await self.database.checkTeamTitleIsUnique(title=title)
    

    @database_error
    async def insertTeam(self, person: PersonModel, team: TeamModel) -> int:
        return await self.database.insertTeam(personModel=person, teamModel=team)
    

    async def updateTeam(self, team: TeamModel) -> int:
        return await self.database.updateTeam(teamModel=team)
    

    async def deleteTeam(self, teamId: int) -> None:    
        await self.database.deleteTeam(teamId=teamId)


    async def queryAdminTeam(self, teamId: int, admin: PersonModel) -> TeamModel:
        return await self.database.queryAdminTeam(teamId=teamId, adminModel=admin)


    async def queryAdminTeams(self, admin: PersonModel) -> List[TeamHeader]:
        return await self.database.queryAdminTeams(adminModel=admin)
    

    async def checkAdminTeam(self, teamId: int, admin: PersonModel) -> bool:
        return await self.database.checkAdminTeam(teamId = teamId, adminModel = admin)

    
    async def checkOutcastMember(self, teamId: int, member: PersonModel) -> bool:
        return await self.database.checkOutcastMember(teamId=teamId, memberModel=member)
    
    
    async def queryTeamSummary(self, teamId: int, member: PersonModel) -> TeamSummary:
        # Query all team data
        teamInfo: TeamInfo = await self.database.queryTeamInfo(teamId=teamId, memberModel=member)

        # Transform raw data

        # Transform CrewInfo to CrewSummary
        crews = list(map(lambda crewInfo: CrewSummary(
            **CrewModel(**crewInfo.model_dump()).model_dump(),
            crewIdStr=even_hex(crewInfo.id),
            as_leader=crewInfo.as_leader,
            mates = crewInfo.mates,
            ),
            teamInfo.crews
        ))

        # Extract default crew
        defaultCrew = next(filter(lambda crew: crew.special == CrewInfo._CREW_SPECIAL_DEFAULT, crews))
        crews[:] = filter(lambda crew: crew.special == CrewInfo._CREW_SPECIAL_UNSET, crews)

        # Compute totalMembers: all mates, all members except mates of defaultCrew 
        totalMembers = len(teamInfo.members) + deque(
            accumulate(map(lambda crew: len(crew.mates), crews), initial=0),
            maxlen = 1).pop()
        
        # Build TeamSummary
        return TeamSummary.model_validate(
            dict(TeamModel.model_validate(teamInfo.model_dump()).model_dump(), **{
                fields(TeamSummary).teamIdStr : even_hex(teamInfo.id),
                fields(TeamSummary).as_admin : teamInfo.as_admin,
                fields(TeamSummary).as_member : teamInfo.as_member,
                fields(TeamSummary).crews : crews,
                fields(TeamSummary).defaultCrew : defaultCrew,
                fields(TeamSummary).members : teamInfo.members,
                fields(TeamSummary).totalMembers : totalMembers,
                fields(TeamSummary).deadlineDaysLeft : 
                    (teamInfo.deadline - datetime.datetime.now()).days 
                        if teamInfo.deadline is not None else None,
                fields(TeamSummary).canAddMember : 
                    not (teamInfo.suspendCompanions and teamInfo.as_member),
                fields(TeamSummary).canRemoveMember : teamInfo.as_member,
                fields(TeamSummary).canAddMemberCrew : teamInfo.enableCrews or teamInfo.as_admin,
            }))


    
    async def canAddTeamMember(self, teamId: int, member: PersonModel) -> bool:
        return await self.database.canAddTeamMember(teamId = teamId, memberModel = member)
    
    @database_error
    async def addTeamMember(self, teamId: int, crewId: Optional[int], member: PersonModel) -> None:
        await self.database.addTeamMember(teamId = teamId, crewId=crewId, memberModel = member)

    
    async def removeTeamMember(self, teamId: int, member: PersonModel) -> None:
        await self.database.removeTeamMember(teamId = teamId, memberModel = member)


    async def checkCrewTitleIsUnique(self, teamId: int, title: str) -> bool:
        return await self.database.checkCrewTitleIsUnique(teamId = teamId, title = title)


    async def insertCrew(self, person: PersonModel, crew: CrewModel) -> int:
        return await self.database.insertCrew(personModel = person, crewModel = crew)


    async def updateCrew(self, crew: CrewModel) -> int:
        return await self.database.updateCrew(crewModel = crew)


    async def deleteCrew(self, crewId: int) -> None:
        await self.database.deleteCrew(crewId=crewId)


    async def queryMemberTeams(self, member: PersonModel) -> List[TeamModel]:
        return await self.database.queryMemberTeams(memberModel = member)
    
    
    async def setCrewMate(self, teamId: int, crewId: int, mate: PersonModel) -> None:
        return await self.database.setCrewMate(teamId=teamId, crewId=crewId, mateModel=mate)
    

    async def queryLeaderCrew(self, crewId: int, person: PersonModel) -> CrewModel:
        return await self.database.queryLeaderCrew(crewId = crewId, personModel=person)



