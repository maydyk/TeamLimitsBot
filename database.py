"""
Database handler

@Author: Denis Maydykovsky
"""
import asyncio
from functools import wraps
from sqlalchemy import delete, func, select, update
from sqlalchemy.engine import Engine
from sqlalchemy.event import listens_for, listen
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from typing import List
from details import Singleton
from entities import *
from models import *



class DatabaseError(Exception):
    pass


class DatabaseErrorDuplicatedTitle(DatabaseError):
    pass


class DatabaseErrorSuspendedCompanions(DatabaseError):
    pass


def connection(method):
    """
    Decorator to wrap session without commit.
    Use it with query
    """
    @wraps(method)
    async def wrapper(self, *args, **kwargs):
        async with self.session_maker() as session:
            return await method(self, *args, session = session, **kwargs)
    return wrapper


def transaction(method):
    """
    Decorator to wrap session with commit.
    Use it to modify data
    """
    @wraps(method)
    async def wrapper(self, *args, **kwargs):
        async with self.session_maker.begin() as session:
            return await method(self, *args, session=session, **kwargs)
    return wrapper


@listens_for(Engine, "connect")
def enable_sqlite_foreign_keys(dbapi_connection, connection_record):
    """
    NOTE: SQLite doesn't execute a foreign keys by default.
    We have to turn it ON!
    """
    
    # check is SQLite.
    if hasattr(dbapi_connection.dbapi, "sqlite"):
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
        """
        Check specified title is unique in all team list. 
        """

        query = select(func.count(Team.title)).where(Team.title == title)
        print(query)
        res = (await session.execute(query)).scalar_one_or_none()
        return (res or 0) == 0
    
    
    @connection
    async def __queryTeam(self, teamId: int, session: AsyncSession) -> Team:
        """
        Helper method to get team by id
        """

        query = select(Team).where(Team.id == teamId)
        print(query)
        return (await session.execute(query)).scalar_one()

    
    @transaction
    async def insertTeam(self, personModel: PersonModel, teamModel: TeamModel, session: AsyncSession) -> int:
        """
        Insert a new team
        """
        
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

        return teamId


    @transaction
    async def updateTeam(self, teamModel: TeamModel, session: AsyncSession) -> int:
        """
        Update specified team
        """

        # Need to know Team ID
        assert(teamModel.id is not None)
        teamId = teamModel.id
    
        query = update(Team).where(Team.id == teamId).values(teamModel.model_dump())
        print(query)

        await session.execute(query)
        return teamId


    @transaction
    async def deleteTeam(self, teamId: int, session: AsyncSession) -> None:
        """
        delete specified team
        """
        
        query = delete(Team).where(Team.id == teamId)
        print(query)
        await session.execute(query)


    @connection
    async def queryAdminTeam(self, teamId: int, adminModel: PersonModel, session: AsyncSession) -> Optional[TeamModel]:
        """
        Return specified team only if person is an administrator of it.
        None overwise.
        """

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
    async def checkAdminTeam(self, teamId: int, adminModel: PersonModel, session: AsyncSession) -> Optional[TeamModel]:
        """
        Check if specified person is administrator of team.
        """
        
        query = (
            select(func.count(Admin.userId))
            .where(
                (Admin.teamId == teamId) &
                (
                    (Admin.userId == adminModel.userId) |
                    (Admin.userName == adminModel.userName)
                )
            )
        )
        print(query)
        
        res = (await session.execute(query)).scalar_one_or_none()

        # The person is a team administrator!
        return bool(res)
    

    @connection
    async def checkMemberTeam(self, teamId: int, memberModel: PersonModel, session: AsyncSession) -> bool:
        """
        Check the person is already member of specified team.
        """
        
        query = select(func.count(Member.teamId)).where(
            (Member.teamId == teamId) &
            ((Member.userId == memberModel.userId) | (Member.userName == memberModel.userName))
        )
        print(query)

        res = (await session.execute(query)).scalar_one_or_none()

        # The person is a team member.
        return bool(res)


    @connection
    async def checkOutcastMember(self, teamId: int, memberModel: PersonModel, session: AsyncSession) -> bool:

        query = (select(func.count(Outcast.userId))
                .where(
                    (Outcast.teamId == teamId) & 
                    (
                        (Outcast.userId == memberModel.userId) |
                        (Outcast.userName == memberModel.userName)
                    )
                )
        )
        print(query)

        res = (await session.execute(query)).scalar_one_or_none()

        # The person is not an outcast!
        return not res
    

    @connection
    async def checkLeaderCrew(self, crewId: int, leaderModel: PersonModel, session: AsyncSession) -> bool:
        query = (
            select(func.count(Leader.crewId))
            .where(
                (Leader.crewId == crewId) &
                (
                    (Leader.userId == leaderModel.userId) |
                    (Leader.userName == leaderModel.userName) 
                )
            )
        )
        print(query)

        res = (await session.execute(query)).scalar_one_or_none()

        # The person is a leader of crew!
        return res is not None


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
        return [TeamHeader(id=teamId, title=title, description=description) 
                for teamId, title, description in res]
    

    @transaction
    async def queryTeamSummary(self, teamId: int, memberModel: Person, session: AsyncSession) -> TeamSummary:

        # Detect member status
        as_member = await self.checkMemberTeam(teamId=teamId, memberModel=memberModel)
        as_admin = await self.checkAdminTeam(teamId=teamId, adminModel=memberModel)

        # Query team definition
        team = (await session.execute(select(Team).where(Team.id == teamId))).scalar_one()
        teamModel = TeamModel.model_validate(team)

        # Query members
        members = (await session.execute(select(Member).where(Member.teamId == teamId).order_by(Member.position))).scalars()
        memberModels = [MemberModel.model_validate(member) for member in members]

        # Query team crews
        crews = (await session.execute(select(Crew).where(Crew.teamId == teamId))).scalars()

        async def make_crew_summary(crew: Crew) -> CrewSummary:
            # Query crew leader
            as_leader = await self.checkLeaderCrew(crewId=crew.id, leaderModel=memberModel)

            # Query mates of crew
            query = select(Member).where(Member.crewId == crew.id)
            mateModels = [MemberModel.model_validate(mate) for mate in await session.execute(query)]
            
            crewModel = CrewModel.model_validate(crew)
            return CrewSummary(as_leader=as_leader, crew=crewModel, mates=mateModels)
        
        # Build crew list
        crewModels = [await make_crew_summary(crew) for crew in crews]
        # crewModels = asyncio.gather(map(make_crew_summary, crews))

        # build team summary
        return TeamSummary(
            as_member=as_member,
            as_admin=as_admin,
            team=teamModel,
            members=memberModels,
            crews=crewModels
        )
        
    @transaction
    async def canAddTeamMember(self, teamId: int, memberModel: PersonModel, session: AsyncSession) -> bool:
        """
        Check the member can be added to specified team
        """

        team = await self.__queryTeam(teamId=teamId)
        if team.suspendCompanions:
            # Check member is already in the team
            return not await self.checkMemberTeam(teamId=teamId, memberModel=memberModel)
        else:
            # Can add companions
            return True


        
    @transaction
    async def addTeamMember(self, teamId: int, crewId: Optional[int], memberModel: PersonModel, session: AsyncSession) -> None:
        """
        Add member to the team
        """

        # Get maximal member number (companion)
        query = select(func.coalesce(func.max(Member.number), -1)).where(
            (Member.teamId == teamId) &
            (
                (Member.userId == memberModel.userId) |
                (Member.userName == memberModel.userName)
            )
        )
        print(query)
        number = (await session.execute(query)).scalar_one()

        # Check team enables companions
        team = await self.__queryTeam(teamId=teamId)
        if team.suspendCompanions and number >= 0:
            raise DatabaseErrorSuspendedCompanions(
                "Cannot insert companion for user "
                f"{memberModel.userId}, {memberModel.userName}")
        
        # Generate the next number (will be zero for first time)
        number += 1

        # Query current position in given team
        query = select(func.coalesce(func.max(Member.position), -1)).where(
            Member.teamId == teamId
        )
        print(query)
        position = (await session.execute(query)).scalar_one()

        # Generate next position
        position += 1

        member = Member(
            **dict(
                memberModel.model_dump(),
                **{
                    "number" : number,
                    "teamId": teamId,
                    "crewId": crewId,
                    "position": position, 
                }
            )
        )
        session.add(member)
        session.commit()
            

    @transaction
    async def removeTeamMember(self, teamId: int, memberModel: MemberModel, session: AsyncSession) -> None:
        """
        Remove member from team.
        """

        # Check team enables companions
        team = await self.__queryTeam(teamId=teamId)
        if team.suspendCompanions:
            # Delete all entities with companions
            query = delete(Member).where(
                (Member.teamId == teamId) & 
                ((Member.userId == memberModel.userId) | (Member.userName == memberModel.userName)))
        else:
            # Delete only last added companion
            query = delete(Member).where(
                (Member.teamId == teamId) &
                ((Member.userId == memberModel.userId) | (Member.userName == memberModel.userName)) &
                (Member.number.in_(select(func.max(Member.number)).where(
                    (Member.teamId == teamId) &
                    ((Member.userId == memberModel.userId) | (Member.userName == memberModel.userName))
                )))
            )
        print(query)

        await session.execute(query)

















