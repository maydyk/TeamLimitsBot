"""
Database handler

@Author: Denis Maydykovsky
"""

import logging

from contextlib import asynccontextmanager
from datetime import datetime
from functools import wraps
from sqlalchemy import delete, func, select, update
from sqlalchemy.engine import Engine
from sqlalchemy.event import listens_for
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, AsyncSessionTransaction, async_sessionmaker, create_async_engine
from typeguard import typechecked
from typing import AsyncIterator, Awaitable, Callable, Final, Iterable, List, Optional, TypeVar, Union

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


class DatabaseDuplicatedTitleError(DatabaseError):
    pass


class DatabasePermissionError(DatabaseError):
    pass


_T = TypeVar("T")

def connection(method: Callable[..., Awaitable[_T]]) -> Callable[..., Awaitable[_T]]: 
    """
    Decorator to wrap the session without commit.
    Use it with the query without modifications.
    """
    @wraps(method)
    async def wrapper(self, *args, **kwargs) -> _T:
        if "session" in kwargs:
            return method(self, *args, *kwargs)
        else:
            async with self.session_maker() as session:
                return await method(self, *args, session=session, **kwargs)
    return wrapper


def transaction(method: Callable[..., Awaitable[_T]]) -> Callable[..., Awaitable[_T]]:
    """
    Decorator to wrap the session with commit.
    Use it to modify data.
    """
    @wraps(method)
    async def wrapper(self, *args, **kwargs) -> _T:
        # Check do call already contain session
        hasSession = any(arg is AsyncSession for arg in args) or "session" in kwargs
        if hasSession in kwargs:
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
    @typechecked
    async def __queryTeam(self, teamId: int, session: AsyncSession) -> Team:
        """
        Helper method to get the team by id
        """
        query = select(Team).where(Team.id == teamId)
        _logger.query(query)
        return (await session.execute(query)).scalar_one()
    

    @connection
    @typechecked
    async def __checkAdminTeam(self, admin: AdminModel, session: AsyncSession) -> bool:
        """
        Check if specified person is administrator of the team.
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
    @typechecked
    async def __checkMemberTeam(self, member: MemberModel, session: AsyncSession) -> bool:
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
    @typechecked
    async def __checkLeaderCrew(self, leader: LeaderModel, session: AsyncSession) -> bool:
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
    @typechecked
    async def queryCrewTeamId(self, crewId: int, session: AsyncSession) -> int:
        """
        Get team for specified crew.
        """
        query = select(Crew.teamId).where(Crew.id == crewId)
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
    @typechecked
    async def insertTeam(self, person: PersonModel, team: TeamModel, session: AsyncSession) -> int:
        """
        Insert a new team
        """
        
        # Disable to insert team with defined ID
        assert team.id is None, "TeamInfo.id for the new model must be None."

        # Build a new team
        if team.title == "" or not await self.checkTeamTitleIsUnique(team.title):
            raise DatabaseDuplicatedTitleError(f"The title for a new team {team.title} is empty or already exists.")
            
        # Insert the new team
        async with nested_transaction(session):
            teamEntity = Team(**teamModel.model_dump())
            session.add(teamEntity)
            await session.flush()
            teamId = teamEntity.id

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
    @typechecked
    async def canUpdateTeam(self, admin: AdminModel, session: AsyncSession) -> bool:
        return await self.__checkAdminTeam(self, admin, session=session)


    @transaction
    @typechecked
    async def updateTeam(self, admin: AdminModel, team: TeamModel, session: AsyncSession) -> int:
        """
        Update specified team
        """

        # Check person is administrator
        if not await self.canUpdateTeam(admin, session=session):
            raise DatabasePermissionError(f"{admin.display_user_name()} cannot update team {team.id} ({team.title})")


        # Need to know Team ID
        assert team.id is not None, "TeamModel.id when updating cannot be None."
        teamId = team.id
    
        query = update(Team).where(Team.id == teamId).values(**team.model_dump())
        _logger.query(query)

        await session.execute(query)
        return teamId

    
    @connection
    @typechecked
    async def canDeleteTeam(self, admin: AdminModel, session: AsyncSession) -> bool:
        return await self.__checkAdminTeam(admin, session = session)
    

    @transaction
    @typechecked
    async def deleteTeam(self, admin: AdminModel, session: AsyncSession) -> None:
        """
        delete specified team
        """
        
        # Check person is administrator
        if not await self.canDeleteTeam(admin, session=session):
            raise DatabasePermissionError(f"{admin.display_user_name()} cannot delete team {admin.teamId}")

        query = delete(Team).where(Team.id == admin.teamId)
        _logger.query(query)
        await session.execute(query)


    @connection
    @typechecked
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
    @typechecked
    async def queryAdminTeamHeaders(self, person: PersonModel, session: AsyncSession) ->List[TeamHeader]:
        query = select(
            Admin.teamId,
            Team.title,
            Team.description,
            ).join(
                Team,
                Team.id == Admin.teamId
            ).where(
                (Admin.userId == person.userId) |
                (Admin.userName == person.userName)
            ).order_by(Team.id)
    
        _logger.query(query)

        res = await session.execute(query)
        return [TeamHeader(id=teamId, title=title, description=description) 
                for teamId, title, description in res]
    

    @connection
    @typechecked
    async def queryMemberTeamHeaders(self, person: PersonModel, session: AsyncSession) -> List[TeamHeader]:

        query = select(
            Member.teamId,
            Team.title,
            Team.description
            ).join(
                Team,
                Team.id == Member.teamId
            ).where(
                (Member.userId == person.userId) |
                (Member.userName == person.userName)
            ).order_by(Team.id)
        _logger.query(query)

        res = await session.execute(query)
        return [TeamHeader(id=teamId, title=title, description=description)
                for teamId, title, description in res]
    

    @connection
    @typechecked
    async def canViewTeam(self, member: MemberModel, session: AsyncSession) -> bool:
        
        query = select(
            func.count(Outcast.userId)
            ).where(
                (Outcast.teamId == member.teamId) &
                ( 
                    (Outcast.userId == member.userId) |
                    (Outcast.userName == member.userName)
                )
            )

        _logger.query(query)

        isOutcast = (await session.execute(query)).scalar_one_or_none()

        # The person is not an outcast!
        return not isOutcast
    

    @connection
    @typechecked
    async def queryTeamData(self, member: MemberModel, session: AsyncSession) -> TeamData:

        teamId: Final[int] = member.teamId

        # Detect member status
        is_member: Final[bool] = await self.__checkMemberTeam(member)
        is_admin: Final[bool] = await self.__checkAdminTeam(member.combineId(AdminModel, teamId))

        # Query team definition
        team: Final[Team] = await self.__queryTeam(teamId)


        def make_mate_data_list(mates: Iterable[Member]) -> List[MemberData]:
            return [MemberData.model_validate(mate) for mate in mates]


        async def make_crew_data(crew: Crew) -> CrewData:
            # Query crew leader
            as_leader = await self.__checkLeaderCrew(member.combineId(LeaderModel, crew.id))

            # Query mates of crew
            query = select(Member).where(Member.crewId == crew.id).order_by(Member.position)
            mates = make_mate_data_list((await session.execute(query)).scalars())

            return CrewData(
                is_admin=is_admin,
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
            is_admin=is_admin,
            is_member=is_member,
            crews=await make_crew_data_list(crews),
            outboards=make_mate_data_list(outboards),
            **TeamModel.model_validate(team).model_dump()
           )
    
    
    @connection
    @typechecked
    async def checkSuspending(self, member: MemberModel, date: datetime, session: AsyncSession) -> bool:        
        query = select(
            func.count(Member.userId)
            ).join_from(
                Team,
                Member,
                Member.teamId == Team.id
            ).join(
                Admin, 
                Admin.teamId == Team.id
            ).where(
                # An admin can do all.
                (Admin.userId == member.userId) |
                (Admin.userName == member.userName) |
                # Stop when recruitment is suspended  
                (not Team.suspendRecruitment) &
                # Stop id deadline is set and is reached.
                (not Team.suspendOnDeadline | (Team.deadline is None) | (Team.deadline <= date))
            )
        _logger.query(query)

        res = (await session.execute(query)).scalar_one_or_none()
        return bool(res)

        
    @connection
    @typechecked
    async def canAddTeamMember(self, member: MemberModel, date: datetime, session: AsyncSession) -> bool:
        """
        Check the member can be added to specified team:
        member can be an administrator, be single if companions are disabled and not be an outcast 
        """

        query = select(
            func.count(Member.userId)
            ).join_from(
                Team,
                Member,
                Member.teamId == Team.id
            ).join(
                Admin, 
                Admin.teamId == Team.id
            ).join(
                Outcast,
                Outcast.teamId == Team.id                
            ).where(
                # An admin can do all.
                (Admin.userId == member.userId) |
                (Admin.userName == member.userName) |
                # Stop when recruitment is suspended  
                (not Team.suspendRecruitment) &
                # Stop id deadline is set and is reached.
                (not Team.suspendOnDeadline | (Team.deadline is None) | (Team.deadline <= date)) &
                # Stop if companions are suspended and the member is already in the team.
                (not Team.suspendCompanions | Member.userId == member.userId) | (Member.userName == member.userName) &
                # Stop if member is NOT an outcast
                ((Outcast.userId != member.userId) & (Outcast.userName != member.userName))
                )
        _logger.query(query)
    
        res = (await session.execute(query)).scalar_one_or_none()

        return bool(res) 

        
    @transaction
    @typechecked
    async def addTeamMember(self, member: MemberModel, crewId: Optional[int], date: datetime, session: AsyncSession) -> None:
        """
        Add member to the team
        """

        # Check permission
        if not await self.canAddTeamMember(member, date, session=session):
            raise DatabasePermissionError(f"{member.display_user_name()} cannot be added to the team {member.teamId}")

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
            

    @connection
    @typechecked
    async def canRemoveTeamMember(self, member: MemberModel, date: datetime, session: AsyncSession) -> bool:
        return await self.checkSuspending(member, date, session=session)
    

    @transaction
    @typechecked
    async def removeTeamMember(self, member: MemberModel, date: datetime, session: AsyncSession) -> None:
        """
        Remove member from the team.
        """

        if not await self.canRemoveTeamMember(member, date, session=session):
            raise DatabasePermissionError(f"{member.display_user_name()} cannot be removed from the team {member.teamId}")

        subquerySuspendCompanions = select(
            Team.suspendCompanions
        ).where(
            Team.id == member.teamId
        ).subquery()
        
        subqueryMaximalNumber = select(
            func.max(Member.number)
        ).where(
            (Member.teamId == member.teamId) &
            ((Member.userId == member.userId) | (Member.userName == member.userName))
        )
        
        query = delete(Member).where(
            # Delete all entities with companions. See below.
            (Member.teamId == member.teamId) &
            ((Member.userId == member.userId) | (Member.userName == member.userName)) &
            
            # Delete only last added companion
            (subquerySuspendCompanions | (Member.number.in_(subqueryMaximalNumber)))
        )

        _logger.query(query)
        await session.execute(query)


    @transaction
    @typechecked
    async def checkCrewTitleIsUnique(self, teamId: int, title: str, session: AsyncSession) -> bool:
        query = select(func.count(Crew.id)).where(
            (Crew.teamId == teamId) &
            (Crew.title == title)
        )
        _logger.query(query)

        res = (await session.execute(query)).scalar_one_or_none()
        return not res
        

    @connection
    @typechecked
    async def canInsertCrew(self, person: Union[MemberModel, AdminModel], date: datetime, session: AsyncSession) -> bool:

        query = select(
            func.count(Team.id)
        ).join_from(
            Team,
            Admin,
            Team.id == Admin.teamId
        ).where(
            # An admin can do all.
            (Admin.userId == person.userId) |
            (Admin.userName == person.userName) |
            # Stop if custom crews are disabled
            (Team.enableCrews) &
            # Stop when recruitment is suspended  
            (not Team.suspendRecruitment) &
            # Stop id deadline is set and is reached.
            (not Team.suspendOnDeadline | (Team.deadline is None) | (Team.deadline <= date))
        )

        _logger.query(query)

        res = (await session.execute(query)).scalar_one_or_none()
        return bool(res)


    @transaction
    @typechecked
    async def insertCrew(self, person: Union[MemberModel, AdminModel], crew: CrewModel, date: datetime, session: AsyncSession) -> int:

        # Disable to insert team with defined ID
        assert crew.id is None, "CrewModel.id for the new created model must be None."

        # Check permissions
        if not await self.canInsertCrew(person, date, session = session):
            raise DatabasePermissionError(f"{person.display_user_name()} is not able to add a crew.")

        # Build a new crew
        if crew.isRegularCrew() and crew.title == "" or not await self.checkCrewTitleIsUnique(teamId=crew.teamId, title=crew.title):
            raise DatabaseDuplicatedTitleError(f"The title for a new crew {crew.title} is already exists.")

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

        async with nested_transaction(session=session):
            session.add(crewEntity)
            await session.flush()
            crewId = crewEntity.id

        # Mark the person as the crew leader
        async with nested_transaction(session=session):
            leaderEntity = Leader(**person.combineId(LeaderModel, crewId).model_dump())
            session.add(leaderEntity)

        return crewId


    @connection
    @typechecked
    async def canUpdateCrew(leader: Union[LeaderModel, AdminModel], date: datetime, session: AsyncSession) -> bool:

        crewId: Final[Optional[int]] = leader.crewId if leader is LeaderModel else None
        
        subqueryLeaderCrew = select(
            func.coalesce(func.count(Leader.crewId), 0)
            ).where(
                (crewId is not None) & (Leader.crewId == crewId) &
                (
                    Leader.userId == leader.userId |
                    Leader.userName == leader.userName
                )
            ).subquery()

        query = select(
            func.count(Team.id)
        ).join_from(
            Team,
            Admin,
            Team.id == Admin.teamId
        ).where(
            # An admin can do all.
            (Admin.userId == leader.userId) |
            (Admin.userName == leader.userName) |
            # Stop if person is not leader or specified crew
            (subqueryLeaderCrew) &
            # Stop if custom crews are disabled
            (Team.enableCrews) &
            # Stop when recruitment is suspended  
            (not Team.suspendRecruitment) &
            # Stop id deadline is set and is reached.
            (not Team.suspendOnDeadline | (Team.deadline is None) | (Team.deadline <= date))
        )

        res = (await session.execute(query)).scalar_one_or_none()
        return bool(res)


    @transaction
    @typechecked
    async def updateCrew(self, leader: Union[LeaderModel, AdminModel], crew: CrewModel, date: datetime, session: AsyncSession) -> int:

        assert crew.id is not None, "CrewModel.id on updating cannot be None"

        if not await self.canUpdateCrew(leader, date, session=session): 
            raise DatabasePermissionError(f"{leader.display_user_name()} is not able to update crew {crew.title}")

        crewId = crew.id
        query = update(Crew).where(Crew.id == crewId).values(crew.model_dump())
        _logger.query(query)

        await session.execute(query)
        return crewId


    @connection
    @typechecked
    async def canDeleteCrew(self, leader: Union[LeaderModel, AdminModel], date: datetime) -> bool:
        # NOTE: The same condition as on update
        return await self.canUpdateCrew(leader, date)
    

    @transaction
    @typechecked
    async def deleteCrew(self, leader: Union[LeaderModel, AdminModel], date: datetime, session: AsyncSession) -> None:

        if not await self.canDeleteCrew(leader, date, session=session): 
            raise DatabasePermissionError(f"{leader.display_user_name()} is not able to update crew {leader.crewId}")

        query = delete(Crew).where(Crew.id == leader.crewId)
        _logger.query(query)
        await session.execute(query)


    @transaction
    @typechecked
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
    @typechecked
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
    