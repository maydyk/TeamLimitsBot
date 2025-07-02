"""
Database handler

@Author: Denis Maydykovsky
"""
from functools import wraps
from sqlalchemy import delete, func, select, update
from sqlalchemy.engine import Engine
from sqlalchemy.event import listens_for, listen
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from typing import Any, Awaitable, Callable, Final, Iterable, List, Optional
from model_fields import fields

from entities import Admin, Crew, Leader, Member, Outcast, Person, Team
from models_base import AdminModel, CrewModel, LeaderModel, MemberModel, PersonModel, TeamHeader, TeamModel
from models_data import CrewData, MemberData, TeamData

import logging

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
    async def checkTeamTitleIsUnique(self, title: str, session: AsyncSession) -> bool:
        """
        Check the specified title is unique in all team list. 
        """

        query = select(func.count(Team.title)).where(Team.title == title)
        _logger.query(query)
        res = (await session.execute(query)).scalar_one_or_none()
        return not res
    
    
    @transaction
    async def insertTeam(self, personModel: PersonModel, teamModel: TeamModel, session: AsyncSession) -> int:
        """
        Insert a new team
        """
        
        # Disable to insert team with defined ID
        assert teamModel.id is None, "TeamInfo.id for the new model must be None."

        # Build a new team
        if teamModel.title == "" or not await self.checkTeamTitleIsUnique(teamModel.title):
            raise DatabaseErrorDuplicatedTitle(f"The title for a new team {teamModel.title} is empty or already exists.")
            
        # Insert the new team
        team = Team(**teamModel.model_dump())
        session.add(team)
        await session.flush()
        teamId = team.id

        # Create a fake crew for the team
        await self.insertCrew(
            personModel = personModel,
            crewModel = CrewModel(
                teamId = teamId,
                title="",
                position=-1,
                special=Crew._CREW_SPECIAL_DEFAULT,
                ),
            session=session,
            )

        
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
        assert teamModel.id is not None, "TeamModel.id when updating cannot be None."
        teamId = teamModel.id
    
        query = update(Team).where(Team.id == teamId).values(**teamModel.model_dump())
        _logger.query(query)

        await session.execute(query)
        return teamId


    @transaction
    async def deleteTeam(self, teamId: int, session: AsyncSession) -> None:
        """
        delete specified team
        """
        
        query = delete(Team).where(Team.id == teamId)
        _logger.query(query)
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
        _logger.query(query)
        
        team = (await session.execute(query)).scalar_one_or_none()
        return TeamModel.model_validate(team) if team else None
        
    
    @connection
    async def queryAdminTeamHeaders(self, adminModel: PersonModel, session: AsyncSession) ->List[TeamHeader]:
        query = (
            select(Admin.teamId, Team.title, Team.description)
            .join(Team, Team.id == Admin.teamId)
            .where(
                (Admin.userId == adminModel.userId) |
                (Admin.userName == adminModel.userName)
            )
            .order_by(Team.id)
        )
        _logger.query(query)

        res = await session.execute(query)
        return [TeamHeader(id=teamId, title=title, description=description) 
                for teamId, title, description in res]
    

    @connection
    async def checkAdminTeam(self, teamId: int, adminModel: PersonModel, session: AsyncSession) -> bool:
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
        _logger.query(query)
        
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
            (
                (Member.userId == memberModel.userId) |
                (Member.userName == memberModel.userName)
            )
        )
        _logger.query(query)

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
        _logger.query(query)

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
        _logger.query(query)

        res = (await session.execute(query)).scalar_one_or_none()

        # The person is a leader of the crew!
        return bool(res)


    @connection
    async def queryTeamData(self, teamId: int, memberModel: Person, session: AsyncSession) -> TeamData:

        # Detect member status
        as_member: Final[bool] = await self.checkMemberTeam(teamId=teamId, memberModel=memberModel)
        as_admin: Final[bool] = await self.checkAdminTeam(teamId=teamId, adminModel=memberModel)

        # Query team definition
        team: Final[Team] = (await session.execute(select(Team).where(Team.id == teamId))).scalar_one()


        def make_mate_data_list(mates: Iterable[Member]) -> List[MemberData]:
            return [MemberData.model_validate(mate) for mate in mates]


        async def make_crew_data(crew: Crew) -> CrewData:
            # Query crew leader
            as_leader = await self.checkLeaderCrew(crewId=crew.id, leaderModel=memberModel)

            # Query mates of crew
            query = select(Member).where(Member.crewId == crew.id).order_by(Member.position)
            mates = make_mate_data_list((await session.execute(query)).scalars())

            return CrewData.model_validate(
                CrewModel.model_validate(crew).model_dump() |
                {
                    fields(CrewData).as_admin: as_admin,
                    fields(CrewData).as_leader: as_leader,
                    fields(CrewData).mates: mates,
                }
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
        return TeamData.model_validate(
            TeamModel.model_validate(team).model_dump() |
            {
                fields(TeamData).as_admin : as_admin,
                fields(TeamData).as_member : as_member,
                fields(TeamData).crews : await make_crew_data_list(crews),
                fields(TeamData).outboards : make_mate_data_list(outboards),
            }
        )
    
        
    @transaction
    async def canAddTeamMember(self, teamId: int, memberModel: PersonModel, session: AsyncSession) -> bool:
        """
        Check the member can be added to specified team
        """

        team = await self.__queryTeam(teamId=teamId)

        # Check member is already in the team
        return not (
            team.suspendCompanions and 
            await self.checkMemberTeam(teamId=teamId, memberModel=memberModel)
        )


        
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
        _logger.query(query)
        number = (await session.execute(query)).scalar_one()

        # Check team enables companions
        team = await self.__queryTeam(teamId=teamId)
        if team.suspendCompanions and number >= 0:
            raise DatabaseErrorSuspendedCompanions(
                "Cannot insert companion for user "
                f"{memberModel.userId}, {memberModel.userName}")
        
        # Generate the next number (will be zero for the first time)
        number += 1

        # Query current position in given team
        query = select(func.coalesce(func.max(Member.position), -1)).where(
            Member.teamId == teamId
        )
        _logger.query(query)
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
    async def insertCrew(self, personModel: PersonModel, crewModel: CrewModel, session: AsyncSession) -> int:
        # Disable to insert team with defined ID
        assert crewModel.id is None, "CrewModel.id for the new created model must be None."

        # Build a new crew
        if crewModel.special == 0 and crewModel.title == "" or not await self.checkCrewTitleIsUnique(teamId=crewModel.teamId, title=crewModel.title):
            raise DatabaseErrorDuplicatedTitle(f"The title for a new crew {crewModel.title} is already exists.")

        # Insert the new crew
        crew = Crew(**crewModel.model_dump())

        # Find the next crew position in the current team
        if crewModel.special == Crew._CREW_SPECIAL_UNSET:
            query = select(func.coalesce(func.max(Crew.position), -1)).where(
                Crew.teamId == crewModel.teamId
            )
            _logger.query(query)
            position = (await session.execute(query)).scalar_one()

            # Generate next position
            crew.position = position + 1


        session.add(crew)
        await session.flush()
        crewId = crew.id

        # Mark the person as a crew leader
        leader = Leader(**LeaderModel.createFromPerson(personModel, crewId).model_dump())
        session.add(leader)

        return crewId

    
    @transaction
    async def updateCrew(self, crewModel: CrewModel, session: AsyncSession) -> int:
        assert crewModel.id is not None, "CrewModel.id on updating cannot be None"

        crewId = crewModel.id
        query = update(Crew).where(Crew.id == crewId).values(crewModel.model_dump())
        _logger.query(query)

        await session.execute(query)
        return crewId
    

    @transaction
    async def deleteCrew(self, crewId: int, session: AsyncSession) -> None:
        query = delete(Crew).where(Crew.id == crewId)
        _logger.query(query)
        await session.execute(query)


    @connection
    async def queryMemberTeams(self, memberModel: PersonModel, session: AsyncSession) -> List[TeamModel]:
        query = select(Team).where(Team.id.in_(
            select(Member.teamId).where(
                (Member.userId == memberModel.userId) |
                (Member.userName == memberModel.userName)
            )
        )).order_by(Team.id)
        _logger.query(query)

        teams = (await session.execute(query)).scalars().all()
        return list(teams)
    

    @transaction
    async def setCrewMate(self, teamId: int, crewId: Optional[int], mateModel: PersonModel, session: AsyncSession) -> None:
        query = update(Member).where(
            (Member.teamId == teamId) &
            (
                (Member.userId == mateModel.userId) |
                (Member.userName == mateModel.userName)
            ) &
            (Member.number.in_(select(func.min(Member.number)).where(
                # NOTE: check both arguments are NULL, that means them are equal.
                func.coalesce(Member.crewId, crewId, False) & 
                func.coalesce((Member.crewId != crewId), True) &
                (Member.teamId == teamId) &
                (
                    (Member.userId == mateModel.userId) |
                    (Member.userName == mateModel.userName)
                )
        )))).values({Member.crewId : crewId})
        _logger.query(query)

        await session.execute(query)


    @connection
    async def queryLeaderCrew(self, crewId: int, personModel: PersonModel, session: AsyncSession) -> Optional[CrewModel]:
        query = (
            select(Crew)
            .join(Admin, Admin.teamId == Crew.teamId)
            .join(Leader, Leader.crewId == Crew.id)
            .where(
                (Crew.id == crewId) &
                (
                    (Admin.userId == personModel.userId) |
                    (Admin.userName == personModel.userName) |
                    (Leader.userId == personModel.userId) |
                    (Leader.userName == personModel.userName)
                )
            )
        )

        crew = (await session.execute(query)).scalar_one_or_none()
        return CrewModel.model_validate(crew) if crew else None


















