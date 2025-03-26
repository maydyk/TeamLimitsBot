"""
Database handler

@Author: Denis Maydykovsky
"""
from contextlib import asynccontextmanager
from functools import wraps
from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from typing import Any, Awaitable, Callable, Dict, List, Tuple

from details import Singleton
from entities import *

class RepositoryError(Exception):
    pass

class RepositoryErrorDuplicatedTitle(RepositoryError):
    pass

def connection(method):
    @wraps(method)
    async def wrapper(self, *args, **kwargs):
        async with self.session_maker() as session:
            try:
                return await method(self, *args, session = session, **kwargs)
            except Exception as e:
                await session.rollback()
                raise e
            finally:
                await session.close()
    return wrapper


class Repository(metaclass=Singleton):
    """
    Database handler
    """

    # __slots__ = ["connection"]
    engine: AsyncEngine
    session_maker: async_sessionmaker

    @classmethod
    def create(cls, database: str):
        # Create an instance
        self = cls()

        # Open the database
        # Note: create_async_engine is not awaitable
        self.engine  = create_async_engine(f"sqlite+aiosqlite:///{database}", echo=__debug__)
        self.session_maker = async_sessionmaker(self.engine, expire_on_commit=False)

        return self

    async def close(self):
        await self.engine.dispose()


    @classmethod
    @asynccontextmanager
    async def build(cls: type, database: str):
        """
        A context manager for the Repository
        """
        repository = cls.create(database)
        try:
            # await repository.setup()
            yield
        except Exception as ex:
            print("Sql exception", ex)
            raise
        finally:
            await repository.close()


    @connection
    async def checkTeamTitleIsUnique(self, title: str, session: AsyncSession) -> bool:
        query = select(func.count(Team.title)).where(Team.title == title)
        print(query)
        res = (await session.execute(query)).scalar_one_or_none()
        return (res or 0) == 0

    
    @connection
    async def insertTeam(self, userId: int, session: AsyncSession, **team_values) -> int:
        # Disable to insert team with defined ID
        assert(not Team.ID in team_values)

        # Build a new team
        title = team_values[Team.TITLE]
        if title == "" or not await self.checkTeamTitleIsUnique(title):
            raise RepositoryErrorDuplicatedTitle(f"Title for a new team {title} is empty or already exists.")
            
        # Insert the new team
        team = Team(**Team.clean_dict(**team_values))
        session.add(team)
        await session.flush()
        teamId = team.id

        # Create a fake crew for the team
        anyCrew = Crew(teamId = teamId, title="", special=Crew.DEFAULT_CREW_SPECIAL)
        session.add(anyCrew)
        await session.flush()
        
        # Add current user ID as administrator
        session.add(Admin(userId = userId, teamId=teamId))

        await session.commit()
        return teamId

    @connection
    async def updateTeam(self, session: AsyncSession, **team_values) -> int:
        # Need to know Team ID
        assert(Team.ID in team_values)
        teamId = team_values[Team.ID]
    
        query = update(Team).where(Team.id == teamId).values(**Team.clean_dict(**team_values))
        print(query)

        await session.execute(query)
        await session.commit()
        return teamId

    @connection
    async def deleteTeam(self, teamId: int, session: AsyncSession) -> None:
        query = delete(Team).where(Team.id == teamId)
        print(query)

        await session.execute(query)
        await session.commit()

    @connection
    async def queryTeam(self, teamId: int, adminId:int, session: AsyncSession) -> Dict[str, Any]:
        query = (
            select(Team)
            .join(Admin, Team.id == Admin.teamId)
            .where((Team.id == teamId) & (Admin.userId == adminId))
        )
        print(query)
        
        team = (await session.execute(query)).scalar_one_or_none()
        return team.as_dict() if team else { }
    
    @connection
    async def queryAdminTeams(self, adminId: int, session: AsyncSession) -> Dict[int, Tuple[str, str]]:
        query = (
            select(Admin.teamId, Team.title, Team.description)
            .join(Team, Team.id == Admin.teamId)
            .where(Admin.userId == adminId)
            .order_by(Team.id)
        )
        print(query)

        res = await session.execute(query)
        d = {teamId : (title, description) for teamId, title, description in res}
        return d







