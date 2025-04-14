"""
module domain

An intermediate layer between database.Repository() and Telegram UI
@Author: Denis Maydykovsky
"""

from aiogram.types import User
from contextlib import asynccontextmanager
from functools import wraps
from details import Singleton
from database import Database, DatabaseError
from models import *

from typing import Any, Dict, Tuple

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


def database_error(method):
    """
    Decorator to translate 'DatabaseError' to 'RepositoryError'
    """
    @wraps(method)
    async def wrapper(self, *args, **kwargs):
        try:
            await method(self, *args, **kwargs)
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
            print("Sql exception", ex)
            raise
        finally:
            await repository.close()


    # def __getattr__(self, item):
    #     try:
    #         return getattr(self.database, item)
    #     except AttributeError:
    #         return getattr(self, item)

    async def checkTeamTitleIsUnique(self, title) -> bool:
        return await self.database.checkTeamTitleIsUnique(title=title)
    

    @database_error
    async def insertTeam(self, person: PersonModel, team: TeamModel) -> int:
        try:
            return await self.database.insertTeam(personModel=person, teamModel=team)
        except DatabaseError as e:
            raise RepositoryError
    

    async def updateTeam(self, team: TeamModel) -> int:
        return await self.database.updateTeam(teamModel=team)
    

    async def deleteTeam(self, teamId: int) -> None:    
        await self.database.deleteTeam(teamId=teamId)


    async def queryAdminTeam(self, teamId: int, admin: PersonModel) -> TeamModel:
        return await self.database.queryAdminTeam(teamId=teamId, adminModel=admin)


    async def queryAdminTeams(self, admin: PersonModel) -> Dict[int, Tuple[str, str]]:
        return await self.database.queryAdminTeams(adminModel=admin)
    

    async def checkAdminTeam(self, teamId: int, admin: PersonModel) -> bool:
        return await self.database.checkAdminTeam(teamId = teamId, adminModel = admin)

    
    async def checkOutcastMember(self, teamId: int, member: PersonModel) -> bool:
        return await self.database.checkOutcastMember(teamId=teamId, memberModel=member)
    
    
    async def queryTeamSummary(self, teamId: int, member: PersonModel) -> TeamSummary:
        return await self.database.queryTeamSummary(teamId=teamId, memberModel=member)
    
    
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




