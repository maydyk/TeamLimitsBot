"""
module domain

An intermediate layer between database.Repository() and Telegram UI
@Author: Denis Maydykovsky
"""

from aiogram.types import User
from contextlib import asynccontextmanager
from entities import Person, Team
from functools import wraps
from details import Singleton
from database import Database
from models import *

from typing import Any, Dict, Tuple

def make_person(user: User) -> PersonModel:
    return PersonModel(
        userId=user.id,
        userName=user.username,
        firstName=user.first_name,
        lastName=user.last_name,
    )


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
    

    async def insertTeam(self, person: PersonModel, team: TeamModel) -> int:
        return await self.database.insertTeam(personModel=person, teamModel=team)
    

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
    
    
    async def addTeamMember(self, teamId: int, crewId: Optional[int], member: PersonModel) -> None:
        await self.database.addTeamMember(teamId = teamId, crewId=crewId, memberModel = member)

    
    async def removeTeamMember(self, teamId: int, member: PersonModel) -> None:
        await self.database.removeTeamMember(teamId = teamId, memberModel = member)



