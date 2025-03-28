"""
Database handler

@Author: Denis Maydykovsky
"""
from functools import wraps
from sqlalchemy import delete, func, select, update
from sqlalchemy.engine import Engine
from sqlalchemy.event import listens_for, listen
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import Pool
from sqlite3 import Connection as SQLite3Connection

from typing import List
from details import Singleton
from entities import *
from models import *


class DatabaseError(Exception):
    pass

class DatabaseErrorDuplicatedTitle(DatabaseError):
    pass

def connection(method):
    @wraps(method)
    async def wrapper(self, *args, **kwargs):
        async with self.session_maker() as session:
            try:
                return await method(self, *args, session = session, **kwargs)
            except Exception as e:
                print(e)
                await session.rollback()
                raise e
            finally:
                await session.close()
    return wrapper

@listens_for(Engine, "connect")
def enable_sqlite_foreign_keys(dbapi_connection, connection_record):
    """
    NOTE: SQLite doesn't execute a foreign keys by default.
    We have to turn it ON!
    """
    # TODO: check is SQLite. Code below doesn't work.
    # if isinstance(dbapi_connection, SQLite3Connection):
    
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON;")
    cursor.close()


class Database:
    """
    Database handler
    """

    engine: AsyncEngine
    session_maker: async_sessionmaker

    def __init__(self, database: str):
        # Open the database
        # Note: create_async_engine is not awaitable
        self.engine  = create_async_engine(f"sqlite+aiosqlite:///{database}", echo=__debug__)
        self.session_maker = async_sessionmaker(self.engine, expire_on_commit=False)


    async def close(self):
        await self.engine.dispose()


    @connection
    async def checkTeamTitleIsUnique(self, title: str, session: AsyncSession) -> bool:
        query = select(func.count(Team.title)).where(Team.title == title)
        print(query)
        res = (await session.execute(query)).scalar_one_or_none()
        return (res or 0) == 0

    
    @connection
    async def insertTeam(self, personModel: PersonModel, teamModel: TeamModel, session: AsyncSession) -> int:
        # Disable to insert team with defined ID
        assert(teamModel.id is None)

        # Build a new team
        if teamModel.title == "" or not await self.checkTeamTitleIsUnique(teamModel.title):
            raise DatabaseErrorDuplicatedTitle(f"Title for a new team {teamModel.title} is empty or already exists.")
            
        # Insert the new team
        team = Team(**teamModel.model_dump())
        session.add(team)
        await session.flush()
        teamId = team.id

        # Create a fake crew for the team
        defaultCrew = Crew(
            **CrewModel(
                teamId = teamId,
                title="",
                special=Crew.DEFAULT_CREW_SPECIAL,
            ).model_dump()
        )
        session.add(defaultCrew)
        await session.flush()
        
        # Add current user as administrator
        admin = Admin(
            **AdminModel.createFromPerson(personModel, teamId).model_dump()
        )
        session.add(admin)

        await session.commit()
        return teamId


    @connection
    async def updateTeam(self, teamModel: TeamModel, session: AsyncSession) -> int:
        # Need to know Team ID
        assert(teamModel.id is not None)
        teamId = teamModel.id
    
        query = update(Team).where(Team.id == teamId).values(teamModel.model_dump())
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
    async def queryTeam(self, teamId: int, adminModel: PersonModel, session: AsyncSession) -> Optional[TeamModel]:
        query = (
            select(Team)
            .join(Admin, Team.id == Admin.teamId)
            .where(
                (Team.id == teamId) & 
                (
                    (Admin.userId == adminModel.userId) |
                    (Admin.userName == adminModel.userName)
                )
            )
        )
        print(query)
        
        team = (await session.execute(query)).scalar_one_or_none()
        return TeamModel.model_validate(team) if team else None
    

    @connection
    async def queryAdminTeams(self, adminModel: PersonModel, session: AsyncSession) ->List[TeamHeader]:
        query = (
            select(Admin.teamId, Team.title, Team.description)
            .join(Team, Team.id == Admin.teamId)
            .where(
                (Admin.userId == adminModel.userId) |
                (Admin.userName == adminModel.userName)
            )
            .order_by(Team.id)
        )
        print(query)

        res = await session.execute(query)
        return [TeamHeader(teamId, title, description) for teamId, title, description in res]
    

    @connection
    async def allowPersonTeam(self, teamId: int, memberModel: Person, session:AsyncSession) -> bool:
        query = (select(func.count(Outcast.userId))
                .where(
                    (Outcast.teamId == teamId) & 
                    (
                        (Outcast.userId == memberModel.userId) or
                        (Outcast.userName == memberModel.userName)
                    )
                )
        )
        print(query)

        res = (await session.execute(query)).scalar_one_or_none()

        # The person is not an outcast!
        return res == None

    @connection
    async def queryTeamSummary(self, teamId: int, session: AsyncSession) -> dict:
        # Prepare result
        result = {
            Team.ID: teamId,
        }

        # Query team title and description
        query = select(Team.title, Team.description).where(Team.id == teamId)
        title, description = (await session.execute(query)).scalar()
        result[Team.TITLE] = title
        result[Team.DESCRIPTION] = description


        query = select(Member).where(Team.id == teamId).order_by(Member.position)
        res = await session.execute(query)

        # TODO: Replace str key to proper constant
        result["MEMBERS"] = [
            { Member.userId: userId, Member.userName: userName, Member.POSITION: position} for
                userId, userName, position in res
        ]






