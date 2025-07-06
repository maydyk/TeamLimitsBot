"""
Database handler

@Author: Denis Maydykovsky
"""

import logging

from contextlib import asynccontextmanager
from functools import wraps
from sqlalchemy import delete, func, select, update
from sqlalchemy.engine import Engine
from sqlalchemy.event import listens_for
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, AsyncSessionTransaction, async_sessionmaker, create_async_engine
from typing import Any, AsyncIterator, Awaitable, Callable, Final, Iterable, List, Optional

from teamlimits.models.base import AdminModel, CrewModel, LeaderModel, MemberModel, PersonModel, OutcastModel, TeamMember, TeamHeader, TeamModel
from teamlimits.models.common import CrewSpecial
from teamlimits.models.fields import fields
from teamlimits.database.entities import Admin, Crew, Leader, Member, Outcast, Team
from teamlimits.database.models_data import CrewData, MemberData, TeamData


# The module logger
class QueryLogger(logging.Logger):
    LEVEL = logging.DEBUG + 1
    LEVEL_NAME = "QUERY"

    def __init__(self, name: str, level: logging = logging.NOTSET):
        logging.Logger.__init__(self, name, level)

    def query(self, msg, *args, **kwargs):
        if self.isEnabledFor(QueryLogger.LEVEL):
            # Yes, logger takes its '*args' as 'args'.
            self._log(QueryLogger.LEVEL, msg, args, **kwargs)

    @classmethod
    def setup_logging(cls):
        logging.addLevelName(QueryLogger.LEVEL, QueryLogger.LEVEL_NAME)
        logging.setLoggerClass(QueryLogger)
        # logging.add

QueryLogger.setup_logging()

_logger = logging.getLogger(__name__)
_logger.addFilter(logging.Filter(__name__))


class DatabaseError(Exception):
    pass


class DatabaseErrorDuplicatedTitle(DatabaseError):
    pass


class DatabaseErrorPermission(DatabaseError):
    pass


class DatabaseErrorSuspendedCompanions(DatabaseError):
    pass


def connection(method: Callable[..., Awaitable[Any]]) -> Callable[..., Awaitable[Any]]: 
    """
    Decorator to wrap the session without commit.
    Use it with the query without modifications.
    """
    @wraps(method)
    async def wrapper(self, *args, **kwargs) -> Any:
        if "session" in kwargs:
            return method(self, *args, *kwargs)
        else:
            async with self.session_maker() as session:
                return await method(self, *args, session=session, **kwargs)
    return wrapper


def transaction(method: Callable[..., Awaitable[Any]]) -> Callable[..., Awaitable[Any]]:
    """
    Decorator to wrap the session with commit.
    Use it to modify data.
    """
    @wraps(method)
    async def wrapper(self, *args, **kwargs) -> Any:
        if "session" in kwargs:
            return await method(self, *args, **kwargs)
        else:
            async with self.session_maker.begin() as session:
                try:
                    return await method(self, *args, session=session, **kwargs)
                except:
                    await session.rollback()
    return wrapper



@asynccontextmanager
async def nested_transaction(session: AsyncSession) -> AsyncIterator[AsyncSessionTransaction]:
    transaction = session.begin_nested()
    try:
        await transaction.start()
        yield
        await transaction.commit()
    except Exception:
        await transaction.rollback()
        raise

    

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

    def __init__(self, database_url: str):
        # Open the database
        # Note: create_async_engine is not awaitable
        self.engine  = create_async_engine(database_url, echo=False)
        self.session_maker = async_sessionmaker(self.engine, expire_on_commit=False)


    async def close(self):
        await self.engine.dispose()


    @connection
    async def __queryTeam(self, teamId: int, session: AsyncSession) -> Team:
        """
        Helper method to get the team by id
        """

        query = select(Team).where(Team.id == teamId)
        _logger.query(query)
        return (await session.execute(query)).scalar_one()
    

    @connection
    async def queryCrewTeamId(self, crewId: int, session: AsyncSession) -> int:
        """
        Get team for specified crew.
        """

        query = select(Crew.teamId).where(Crew.id == crewId)
        _logger.query(query)
        return (await session.execute(query)).scalar_one()


    @connection
    async def checkCrewsAreEnabled(self, teamId: int, session: AsyncSession) -> bool:
        """
        Are custom crews is enabled for the team?
        """
    
        query = select(Team.enableCrews).where(Team.id == teamId)
        _logger.query(query)
        return (await session.execute(query)).scalar_one()


    
    @connection
    async def checkTeamTitleIsUnique(self, title: str, session: AsyncSession) -> bool:
        """
        Check the specified title is unique in all team list. 
        """

        query = select(func.count(Team.title)).where(Team.title == title)
        _logger.query(query)
        res = (await session.execute(query)).scalar_one_or_none()
        return not res
    
    
    @transaction
    async def insertTeam(self, person: PersonModel, teamModel: TeamModel, session: AsyncSession) -> int:
        """
        Insert a new team
        """
        
        # Disable to insert team with defined ID
        assert teamModel.id is None, "TeamInfo.id for the new model must be None."

        # Build a new team
        if teamModel.title == "" or not await self.checkTeamTitleIsUnique(teamModel.title):
            raise DatabaseErrorDuplicatedTitle(f"The title for a new team {teamModel.title} is empty or already exists.")
            
        # Insert the new team
        async with nested_transaction(session):
            team = Team(**teamModel.model_dump())
            session.add(team)
            await session.flush()
            teamId = team.id

        # Add current user as administrator
        # NOTE: Before inserting default crew!
        async with nested_transaction(session):
            admin = Admin(**person.combineId(AdminModel, teamId).model_dump())
            session.add(admin)
            await session.flush()


        # Create a fake crew for the team
        # NOTE: After insert
        async with nested_transaction(session):
            await self.insertCrew(
                person = person,
                crew = CrewModel(
                    teamId = teamId,
                    title="",
                    position=-1,
                    special=CrewSpecial.CREW_SPECIAL_DEFAULT,
                    ),
                session=session,
                )

        
        return teamId


    @transaction
    async def updateTeam(self, admin: AdminModel, team: TeamModel, session: AsyncSession) -> int:
        """
        Update specified team
        """


        # Check person is administrator
        if not await self.checkAdminTeam(admin, session=session):
            raise DatabaseErrorPermission(f"{admin.display_user_name()} cannot update team {team.id} ({team.title})")


        # Need to know Team ID
        assert team.id is not None, "TeamModel.id when updating cannot be None."
        teamId = team.id
    
        query = update(Team).where(Team.id == teamId).values(**team.model_dump())
        _logger.query(query)

        await session.execute(query)
        return teamId


    @transaction
    async def deleteTeam(self, admin: AdminModel, session: AsyncSession) -> None:
        """
        delete specified team
        """
        
        # Check person is administrator
        if not await self.checkAdminTeam(admin, session=session):
            raise DatabaseErrorPermission(f"{admin.display_user_name()} cannot delete team {admin.teamId}")

        query = delete(Team).where(Team.id == admin.teamId)
        _logger.query(query)
        await session.execute(query)


    @connection
    async def queryAdminTeam(self, admin: AdminModel, session: AsyncSession) -> Optional[TeamModel]:
        """
        Return specified team only if person is an administrator of it.
        None overwise.
        """

        query = (
            select(Team)
            .join(Admin, Team.id == Admin.teamId)
            .where(
                (Team.id == admin.teamId) &
                (
                    (Admin.userId == admin.userId) |
                    (Admin.userName == admin.userName)
                )
            )
        )
        _logger.query(query)
        
        team = (await session.execute(query)).scalar_one_or_none()
        return TeamModel.model_validate(team) if team else None
        
    
    @connection
    async def queryAdminTeamHeaders(self, admin: PersonModel, session: AsyncSession) ->List[TeamHeader]:
        query = (
            select(Admin.teamId, Team.title, Team.description)
            .join(Team, Team.id == Admin.teamId)
            .where(
                (Admin.userId == admin.userId) |
                (Admin.userName == admin.userName)
            )
            .order_by(Team.id)
        )
        _logger.query(query)

        res = await session.execute(query)
        return [TeamHeader(id=teamId, title=title, description=description) 
                for teamId, title, description in res]
    

    @connection
    async def checkAdminTeam(self, admin: AdminModel, session: AsyncSession) -> bool:
        """
        Check if specified person is administrator of team.
        """
        
        query = (
            select(func.count(Admin.userId))
            .where(
                (Admin.teamId == admin.teamId) &
                (
                    (Admin.userId == admin.userId) |
                    (Admin.userName == admin.userName)
                )
            )
        )
        _logger.query(query)
        
        res = (await session.execute(query)).scalar_one_or_none()

        # The person is a team administrator!
        return bool(res)
    

    @connection
    async def checkMemberTeam(self, member: MemberModel, session: AsyncSession) -> bool:
        """
        Check the person is already member of specified team.
        """
        
        query = select(func.count(Member.teamId)).where(
            (Member.teamId ==member.teamId) &
            (
                (Member.userId == member.userId) |
                (Member.userName == member.userName)
            )
        )
        _logger.query(query)

        res = (await session.execute(query)).scalar_one_or_none()

        # The person is a team member.
        return bool(res)


    @connection
    async def checkOutcastMember(self, outcast: OutcastModel, session: AsyncSession) -> bool:

        query = (select(func.count(Outcast.userId))
                .where(
                    (Outcast.teamId == outcast.teamId) & 
                    (
                        (Outcast.userId == outcast.userId) |
                        (Outcast.userName == outcast.userName)
                    )
                )
        )
        _logger.query(query)

        res = (await session.execute(query)).scalar_one_or_none()

        # The person is an outcast!
        return bool(res)
    

    @connection
    async def checkLeaderCrew(self, leader: LeaderModel, session: AsyncSession) -> bool:
        query = (
            select(func.count(Leader.crewId))
            .where(
                (Leader.crewId == leader.crewId) &
                (
                    (Leader.userId == leader.userId) |
                    (Leader.userName == leader.userName) 
                )
            )
        )
        _logger.query(query)

        res = (await session.execute(query)).scalar_one_or_none()

        # The person is a leader of the crew!
        return bool(res)


    @connection
    async def queryTeamData(self, member: MemberModel, session: AsyncSession) -> TeamData:

        teamId: Final[int] = member.teamId

        # Detect member status
        as_member: Final[bool] = await self.checkMemberTeam(member)
        as_admin: Final[bool] = await self.checkAdminTeam(member.combineId(AdminModel, teamId))

        # Query team definition
        team: Final[Team] = await self.__queryTeam(teamId)


        def make_mate_data_list(mates: Iterable[Member]) -> List[MemberData]:
            return [MemberData.model_validate(mate) for mate in mates]


        async def make_crew_data(crew: Crew) -> CrewData:
            # Query crew leader
            as_leader = await self.checkLeaderCrew(member.combineId(LeaderModel, crew.id))

            # Query mates of crew
            query = select(Member).where(Member.crewId == crew.id).order_by(Member.position)
            mates = make_mate_data_list((await session.execute(query)).scalars())

            return CrewData(
                as_admin=as_admin,
                as_leader=as_leader,
                mates=mates,
                **CrewModel.model_validate(crew).model_dump(),
            )
        
        
        async def make_crew_data_list(crews: Iterable[Crew]) -> List[CrewData]:
            return [await make_crew_data(crew) for crew in crews]
        
        # Query team crews
        crews = (await session.execute(select(Crew).where(Crew.teamId == teamId).order_by(Crew.position))).scalars()

        # Query members without crew.
        outboards = (await session.execute(
            select(Member)
            .where((Member.teamId == teamId) 
                   and (Member.crewId == None)
                   )
            .order_by(Member.position))
        ).scalars()

        # build team summary
        return TeamData(
            as_admin=as_admin,
            as_member=as_member,
            crews=await make_crew_data_list(crews),
            outboards=make_mate_data_list(outboards),
            **TeamModel.model_validate(team).model_dump()
           )
    
        
    @transaction
    async def canAddTeamMember(self, member: MemberModel, session: AsyncSession) -> bool:
        """
        Check the member can be added to specified team
        """

        team: Final[TeamModel] = await self.__queryTeam(teamId=member.teamId)

        # Check member is already in the team
        return not (
            team.suspendCompanions and await self.checkMemberTeam(member)
            ) and not await self.checkOutcastMember(member.combineId(OutcastModel, member.teamId))


        
    @transaction
    async def addTeamMember(self, member: MemberModel, crewId: Optional[int], session: AsyncSession) -> None:
        """
        Add member to the team
        """
        if await self.checkOutcastMember(member.combineId(OutcastModel, member.teamId)):
            raise DatabaseErrorPermission(f"{member.display_user_name()} is an outcast for the team {member.teamId}")

        # Get maximal member number (companion)
        query = select(func.coalesce(func.max(Member.number), -1)).where(
            (Member.teamId == member.teamId) &
            (
                (Member.userId == member.userId) |
                (Member.userName == member.userName)
            )
        )
        _logger.query(query)
        number = (await session.execute(query)).scalar_one()

        # Check team enables companions
        team = await self.__queryTeam(teamId=member.teamId)
        if team.suspendCompanions and number >= 0:
            raise DatabaseErrorSuspendedCompanions(
                "Cannot insert companion for user "
                f"{member.userId}, {member.userName}")
        
        # Generate the next number (will be zero for the first time)
        number += 1

        # Query current position in given team
        query = select(func.coalesce(func.max(Member.position), -1)).where(
            Member.teamId == member.teamId
        )
        _logger.query(query)
        position = (await session.execute(query)).scalar_one()

        # Generate next position
        position += 1

        memberEntity = Member(
            **TeamMember(
                number=number,
                crewId=crewId,
                position=position,
                **member.model_dump()
            ).model_dump()
        )
        session.add(memberEntity)
            

    @transaction
    async def removeTeamMember(self, member: MemberModel, session: AsyncSession) -> None:
        """
        Remove member from the team.
        """

        # Check team enables companions
        team = await self.__queryTeam(teamId=member.teamId)
        if team.suspendCompanions:
            # Delete all entities with companions
            query = delete(Member).where(
                (Member.teamId == member.teamId) & 
                ((Member.userId == member.userId) | (Member.userName == member.userName)))
        else:
            # Delete only last added companion
            query = delete(Member).where(
                (Member.teamId == member.teamId) &
                ((Member.userId == member.userId) | (Member.userName == member.userName)) &
                (Member.number.in_(select(func.max(Member.number)).where(
                    (Member.teamId == member.teamId) &
                    ((Member.userId == member.userId) | (Member.userName == member.userName))
                )))
            )
        _logger.query(query)
        await session.execute(query)


    @transaction
    async def checkCrewTitleIsUnique(self, teamId: int, title: str, session: AsyncSession) -> bool:
        query = select(func.count(Crew.id)).where(
            (Crew.teamId == teamId) &
            (Crew.title == title)
        )
        _logger.query(query)

        res = (await session.execute(query)).scalar_one_or_none()
        return not res
        

    @transaction
    async def insertCrew(self, person: PersonModel, crew: CrewModel, session: AsyncSession) -> int:
        # Disable to insert team with defined ID
        assert crew.id is None, "CrewModel.id for the new created model must be None."

        # Check permissions
        if not (await self.checkAdminTeam(person.combineId(AdminModel, crew.teamId)) or
            await self.checkCrewsAreEnabled(crew.teamId)
            ):
            raise DatabaseErrorPermission(f"{person.display_user_name()} is not able to add a crew.")
        

        # Build a new crew
        if crew.isRegularCrew() and crew.title == "" or not await self.checkCrewTitleIsUnique(teamId=crew.teamId, title=crew.title):
            raise DatabaseErrorDuplicatedTitle(f"The title for a new crew {crew.title} is already exists.")

        # Insert the new crew
        crewEntity = Crew(**crew.model_dump())

        # Find the next crew position in the current team
        if crew.isRegularCrew():
            query = select(func.coalesce(func.max(Crew.position), -1)).where(
                Crew.teamId == crew.teamId
            )
            _logger.query(query)
            position = (await session.execute(query)).scalar_one()

            # Generate next position
            crewEntity.position = position + 1


        session.add(crewEntity)
        await session.flush()
        crewId = crewEntity.id

        # Mark the person as a crew leader
        leaderEntity = Leader(**person.combineId(LeaderModel, crewId).model_dump())
        session.add(leaderEntity)

        return crewId

    
    @transaction
    async def updateCrew(self, leader: PersonModel, crew: CrewModel, session: AsyncSession) -> int:
        assert crew.id is not None, "CrewModel.id on updating cannot be None"

        if not (await self.checkAdminTeam(leader.combineId(AdminModel, crew.teamId)) or
                await self.checkLeaderCrew(leader)
            ): 
            raise DatabaseErrorPermission(f"{leader.display_user_name()} is not able to update crew {crew.title}")

        crewId = crew.id
        query = update(Crew).where(Crew.id == crewId).values(crew.model_dump())
        _logger.query(query)

        await session.execute(query)
        return crewId
    

    @transaction
    async def deleteCrew(self, leader: LeaderModel, session: AsyncSession) -> None:
        teamId = self.queryCrewTeamId(leader.crewId)

        if not (await self.checkAdminTeam(leader.combineId(AdminModel, teamId)) or
                await self.checkLeaderCrew(leader)
            ): 
            raise DatabaseErrorPermission(f"{leader.display_user_name()} is not able to update crew {leader.crewId}")

        query = delete(Crew).where(Crew.id == leader.crewId)
        _logger.query(query)
        await session.execute(query)


    @connection
    async def queryMemberTeams(self, member: PersonModel, session: AsyncSession) -> List[TeamModel]:
        query = select(Team).where(Team.id.in_(
            select(Member.teamId).where(
                (Member.userId == member.userId) |
                (Member.userName == member.userName)
            )
        )).order_by(Team.id)
        _logger.query(query)

        teams = (await session.execute(query)).scalars().all()
        return list(teams)
    

    @transaction
    async def setCrewMate(self, mate: MemberModel, crewId: Optional[int], session: AsyncSession) -> None:
        query = update(Member).where(
            (Member.teamId == mate.teamId) &
            (
                (Member.userId == mate.userId) |
                (Member.userName == mate.userName)
            ) &
            (Member.number.in_(select(func.min(Member.number)).where(
                # NOTE: check both arguments are NULL, that means them are equal.
                func.coalesce(Member.crewId, crewId, False) & 
                func.coalesce((Member.crewId != crewId), True) &
                (Member.teamId == mate.teamId) &
                (
                    (Member.userId == mate.userId) |
                    (Member.userName == mate.userName)
                )
        )))).values({Member.crewId : crewId})
        _logger.query(query)

        await session.execute(query)


    @connection
    async def queryLeaderCrew(self, leader: PersonModel, crewId: int, session: AsyncSession) -> Optional[CrewModel]:
        query = (
            select(Crew)
            .join(Admin, Admin.teamId == Crew.teamId)
            .join(Leader, Leader.crewId == Crew.id)
            .where(
                (Crew.id == crewId) &
                (
                    (Admin.userId == leader.userId) |
                    (Admin.userName == leader.userName) |
                    (Leader.userId == leader.userId) |
                    (Leader.userName == leader.userName)
                )
            )
        )

        crew = (await session.execute(query)).scalar_one_or_none()
        return CrewModel.model_validate(crew) if crew else None


















