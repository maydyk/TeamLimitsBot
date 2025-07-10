"""
module domain

An intermediate layer between database and Telegram UI
@Author: Denis Maydykovsky
"""

import logging

from contextlib import asynccontextmanager
from datetime import datetime
from functools import wraps
from itertools import filterfalse
from pprint import pprint
from sqlalchemy import Select, case, delete, func, literal, not_, select, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from typeguard import typechecked
from typing import Any, Awaitable, AsyncIterator, Callable, Dict, Iterable, Final, List, Optional, ParamSpec, Self, Tuple, TypeVar, Union, cast

from teamlimits.database.connection import Connection
from teamlimits.database.entities import Admin, Crew, Leader, Member, Outcast, Team

from teamlimits.models import (
    CrewSpecial,
    ######
    AdminModel,
    CrewModel,
    LeaderModel,
    PersonModel,
    MemberModel,
    TeamHeader,
    TeamMember,
    TeamModel,
    ######
    MemberData,
    TeamData,
    CrewData,
)


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

QueryLogger.setup_logging()

_logger: QueryLogger = cast(QueryLogger, logging.getLogger(__name__))

_logger.addFilter(logging.Filter(__name__))


class RepositoryError(Exception):
    pass


class RepositoryDuplicatedTitleError(RepositoryError):
    pass


class RepositoryPermissionError(RepositoryError):
    pass


@typechecked
def _print_args(message: str, *args, **kwargs):
    print(message)
    for index, arg in enumerate(args):
        print(f"{index}:{arg}")
    
    for key, value in kwargs.items():
        print(f"{key}={value}")

    print("---")


@asynccontextmanager
async def nested_transaction(session: AsyncSession) -> AsyncIterator[AsyncSession]:
    transaction = session.begin_nested()
    try:
        await transaction.start()
        yield
        await transaction.commit()
    except Exception:
        await transaction.rollback()
        raise


_P = ParamSpec("params")
_R = TypeVar("result")


# Marker 
class SessionHandler:
    args: List[Any]
    kwargs: Dict[str, Any]
    owner: "Repository"

    @typechecked
    def __init__(self: Self, _owner: "Repository", _args: Tuple[Any, ...], _kwargs: Dict[str, Any]):
        # Remove self (Repository) from arguments to enable recursive call
        self.args = list(filterfalse(lambda arg: arg is _owner, _args))
        self.kwargs = _kwargs.copy()
        self.owner = _owner


    @typechecked
    def has_session(self: Self) -> bool:
        kwSession = self.kwargs.get("session")
        assert kwSession is None or isinstance(kwSession, AsyncSession), "session= must be an AsyncSession."

        # Combine session from arguments and from key-words
        iterSession = (arg for arg in self.args + [kwSession] if isinstance(arg, AsyncSession))
        
        session = next(iterSession, None)

        # AsyncSession must be only one or none.
        try:
            next(iterSession)
            assert False, "Duplicated AsyncSession in positional arguments."
        except StopIteration:
            # OK, AsyncSession is only one or none.
            return bool(session)

    @typechecked
    async def invoke(self: Self, method: Callable[_P, Awaitable[_R]]) -> _R:
        return await method(self.owner, *self.args, **self.kwargs)  



class Repository:

    connection: Connection

    def __init__(self, _connection: Connection):
        self.connection = _connection


    def session(method: Callable[_P, Awaitable[_R]]) -> Callable[_P, Awaitable[_R]]:
        """
        Decorator to wrap the session without commit on exit.
        """
        @wraps(method)
        async def wrapper(self: Self, *args, **kwargs) -> _R:
            handler = SessionHandler(self, args, kwargs)

            if handler.has_session():
                return await handler.invoke(method)
            else:
                # Perform call with session
                async with self.connection.make_session(False) as session:
                    # _print_args(f"Call {method.__name__} ->", *args, **kwargs)
                    return await method(self,  *args, session = session, **kwargs)
        
        return wrapper


    def transaction(method: Callable[_P, Awaitable[_R]]) -> Callable[_P, Awaitable[_R]]:
        """
        Decorator to wrap the session with commit on exit.
        """
        @wraps(method)
        async def wrapper(self: Self, *args, **kwargs) -> _R:
            handler = SessionHandler(self, args, kwargs)

            if handler.has_session():
                return handler.invoke(method)
            else:
                # Perform call with session
                async with self.connection.make_session(True) as session:
                    # _print_args(f"Call {method.__name__} ->", *args, **kwargs)
                    return await method(self,  *args, session = session, **kwargs)
        
        return wrapper

    @session
    @typechecked
    async def __print_select_result(self: Self, query: Select[Tuple], session: AsyncSession):
        res = (await session.execute(query)).mappings().all()
        pprint(res)


    @session
    @typechecked
    async def __queryTeam(self: Self, teamId: int, session: AsyncSession) -> Team:
        """
        Helper method to get the team by id
        """
        query = select(Team).where(Team.id == teamId)
        _logger.query(query)
        return (await session.execute(query)).scalar_one()
    

    @session
    @typechecked
    async def __checkAdminTeam(self: Self, admin: AdminModel, session: AsyncSession) -> bool:
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

    @session
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


    @session
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


    @session
    @typechecked
    async def queryCrewTeamId(self, crewId: int, session: AsyncSession) -> int:
        """
        Get team for specified crew.
        """
        query = select(Crew.teamId).where(Crew.id == crewId)
        _logger.query(query)
        return (await session.execute(query)).scalar_one()

    
    @session
    @typechecked
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
            raise RepositoryDuplicatedTitleError(f"The title for a new team {team.title} is empty or already exists.")
            
        # Insert the new team
        async with nested_transaction(session):
            teamEntity = Team(**team.model_dump())
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
    async def canUpdateTeam(self: Self, admin: AdminModel, session: AsyncSession) -> bool:
        return await self.__checkAdminTeam(self, admin, session=session)


    @transaction
    @typechecked
    async def updateTeam(self, admin: AdminModel, team: TeamModel, session: AsyncSession) -> int:
        """
        Update specified team
        """
        # Need to know Team ID
        assert team.id is not None, "TeamModel.id when updating cannot be None."
        assert admin.teamId == team.id, "Admin can update only owning command."
        
        teamId = team.id

        # Check person is administrator
        if not await self.canUpdateTeam(admin, session=session):
            raise RepositoryPermissionError(f"{admin.display_user_name()} cannot update team {team.id} ({team.title})")

        query = update(Team).where(Team.id == teamId).values(**team.model_dump())
        _logger.query(query)

        await session.execute(query)
        return teamId

    
    @session
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
            raise RepositoryPermissionError(f"{admin.display_user_name()} cannot delete team {admin.teamId}")

        query = delete(Team).where(Team.id == admin.teamId)
        _logger.query(query)
        await session.execute(query)


    @session
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
        
    
    @session
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
    

    @session
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
            ).group_by(Member.teamId).order_by(Team.id)
        _logger.query(query)

        await self.__print_select_result(query, session=session)

        res = await session.execute(query)
        return [TeamHeader(id=teamId, title=title, description=description)
                for teamId, title, description in res]
    

    @session
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


    @session
    @typechecked
    async def canInsertTeamMember(self, member: MemberModel, date: datetime, session: AsyncSession) -> bool:
        """
        Check the member can be added to specified team:
        member can be an administrator, be single if companions are disabled and not be an outcast 
        """
        selectedTeam = select(
            Team.id,
            Team.deadline,
            Team.suspendRecruitment,
            Team.suspendCompanions,
            Team.suspendOnDeadline,
        ).where(
            Team.id == member.teamId
        ).subquery().alias("selected_team")

        teamAdmins = select(
            Admin
        ).where(
            Admin.teamId == member.teamId
        ).subquery().alias("team_admins")

        teamMembers = select(
            Member.userId, Member.userName, Member.teamId,
        ).where(
            Member.teamId == member.teamId
        ).subquery().alias("team_members")

        isMemberOnTeam = select(
            func.coalesce(func.count(teamMembers.c.teamId), 0)
        ).where(
            (teamMembers.c.userId == member.userId) |
            (teamMembers.c.userName == member.userName)
        ).subquery().alias("member_in_team")

        teamOutcasts = select(
            Outcast.userId, Outcast.userName, Outcast.teamId,
        ).where(
            Outcast.teamId == member.teamId
        ).subquery().alias("team_outcasts")

        isMemberOutcast = select(
            func.coalesce(func.count(teamOutcasts.c.teamId), 0)
        ).where(
            (teamOutcasts.c.userId == member.userId) |
            (teamOutcasts.c.userName == member.userName)
        ).subquery().alias("member_is_outcast")

        query = select(
            # func.count(selectedTeam.c.id),
            selectedTeam,
            teamAdmins,
            teamMembers,
            teamOutcasts,
            ).join(
                teamAdmins, 
                teamAdmins.c.teamId == selectedTeam.c.id,
                isouter=True
            ).join(
                teamMembers,
                teamMembers.c.teamId == selectedTeam.c.id,
                isouter=True
            ).join(
                teamOutcasts,
                teamOutcasts.c.teamId == selectedTeam.c.id,
                isouter=True,             
            ).where(
                # An admin can do all.
                (not_(teamAdmins.c.userId.is_(None)) & (teamAdmins.c.userId == member.userId)) |
                (not_(teamAdmins.c.userName.is_(None)) & (teamAdmins.c.userName == member.userName)) |
                # Stop when recruitment is suspended  
                not_(selectedTeam.c.suspendRecruitment) &
                # Stop id deadline is set and is reached.
                (
                    not_(selectedTeam.c.suspendOnDeadline) | 
                    (selectedTeam.c.deadline.is_(None)) | 
                    (selectedTeam.c.deadline <= date)
                ) &
                # Stop if companions are suspended and the member is already in the team.
                (
                    not_(selectedTeam.c.suspendCompanions) | 
                    # We can be inserted to an empty team
                    teamMembers.c.teamId.is_(None) | literal(0).in_(isMemberOnTeam)
                ) & 
                # Stop if member is NOT an outcast
                literal(0).in_(isMemberOutcast)
            )
        
        _logger.query(query)
    
        # await self.__print_select_result(query, session=session)

        res = (await session.execute(query)).fetchall() #.scalar_one_or_none()

        return bool(res) 

        
    @transaction
    @typechecked
    async def insertTeamMember(self, member: MemberModel, crewId: Optional[int], date: datetime, session: AsyncSession) -> None:
        """
        Add member to the team
        """

        # Check permission
        if not await self.canInsertTeamMember(member, date, session=session):
            raise RepositoryPermissionError(f"{member.display_user_name()} cannot be added to the team {member.teamId}")

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
            

    @session
    @typechecked
    async def canRemoveTeamMember(self, member: MemberModel, date: datetime, session: AsyncSession) -> bool:
        selectedTeam = select(
            Team.id,
            Team.suspendRecruitment,
            Team.suspendOnDeadline,
            Team.deadline,
        ).where(
            Team.id == member.teamId
        ).subquery().alias("selected_team")
        
        teamAdmins = select(
            Admin.teamId, Admin.userId, Admin.userName
        ).where(
            Admin.teamId == member.teamId
        ).subquery().alias("selected_member")

        query = select(
            func.count(selectedTeam.c.id)
            ).join(
                Member,
                Member.teamId == selectedTeam.c.id
            ).join(
                teamAdmins, 
                teamAdmins.c.teamId == selectedTeam.c.id,
                isouter=True,
            ).where(
                # An admin can do all.
                not_(teamAdmins.c.userId.is_(None)) & (teamAdmins.c.userId == member.userId) |
                not_(teamAdmins.c.userName.is_(None)) & (teamAdmins.c.userName == member.userName) |
                # Stop if person is not a member
                (
                    (Member.userId == member.userId) |
                    (Member.userName == member.userName)
                ) &
                # Stop when recruitment is suspended  
                not_(selectedTeam.c.suspendRecruitment) &
                # Stop id deadline is set and is reached.
                (
                    not_(selectedTeam.c.suspendOnDeadline) | 
                    (selectedTeam.c.deadline.is_(None)) | 
                    (selectedTeam.c.deadline <= date)
                )
            )
        
        _logger.query("full query: %s", str(query))

        res = (await session.execute(query)).scalar_one_or_none()
        return bool(res)
    

    @transaction
    @typechecked
    async def removeTeamMember(self, member: MemberModel, date: datetime, session: AsyncSession) -> None:
        """
        Remove the member from the team.
        """

        if not await self.canRemoveTeamMember(member, date, session=session):
            raise RepositoryPermissionError(f"{member.display_user_name()} cannot be removed from the team {member.teamId}")

        suspendCompanions = select(
            case(
                (Team.suspendCompanions, 1),
                else_= 0,
            )
        ).join(
            Admin,
            Admin.teamId == Team.id
        ).where(
            (Team.id == member.teamId) &
            # Exclude an Admin from the suspendCompanions restriction.
            (Admin.userId != member.userId) &
            (Admin.userName != member.userName)
        ).subquery().alias("suspended_companions")
        
        maximalNumber = select(
            func.max(Member.number)
        ).where(
            (Member.teamId == member.teamId) &
            ((Member.userId == member.userId) | (Member.userName == member.userName))
        ).subquery().alias("maximal_number")
        
        query = delete(Member).where(
            # Delete all entities with companions. See below.
            (Member.teamId == member.teamId) &
            ((Member.userId == member.userId) | (Member.userName == member.userName)) &
            
            # Delete only last added companion
            (literal(1).in_(suspendCompanions) | (Member.number.in_(maximalNumber)))
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
        

    @session
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
            not_(Team.suspendRecruitment) &
            # Stop id deadline is set and is reached.
            (not_(Team.suspendOnDeadline) | (Team.deadline.is_(None)) | (Team.deadline <= date))
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
            raise RepositoryPermissionError(f"{person.display_user_name()} is not able to add a crew.")

        # Build a new crew
        if crew.isRegularCrew() and crew.title == "" or not await self.checkCrewTitleIsUnique(teamId=crew.teamId, title=crew.title):
            raise RepositoryDuplicatedTitleError(f"The title for a new crew {crew.title} is already exists.")

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


    @session
    @typechecked
    async def canUpdateCrew(leader: Union[LeaderModel, AdminModel], date: datetime, session: AsyncSession) -> bool:

        crewId: Final[Optional[int]] = leader.crewId if leader is LeaderModel else None
        
        subqueryLeaderCrew = select(
            func.coalesce(func.count(Leader.crewId), 0)
            ).where(
                (not_(crewId.is_(None))) & (Leader.crewId == crewId) &
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
            not_(Team.suspendRecruitment) &
            # Stop id deadline is set and is reached.
            (not_(Team.suspendOnDeadline) | Team.deadline.is_(None) | (Team.deadline <= date))
        )

        res = (await session.execute(query)).scalar_one_or_none()
        return bool(res)


    @transaction
    @typechecked
    async def updateCrew(self, leader: Union[LeaderModel, AdminModel], crew: CrewModel, date: datetime, session: AsyncSession) -> int:

        assert crew.id is not None, "CrewModel.id on updating cannot be None"

        if not await self.canUpdateCrew(leader, date, session=session): 
            raise RepositoryPermissionError(f"{leader.display_user_name()} is not able to update crew {crew.title}")

        crewId = crew.id
        query = update(Crew).where(Crew.id == crewId).values(crew.model_dump())
        _logger.query(query)

        await session.execute(query)
        return crewId


    @session
    @typechecked
    async def canDeleteCrew(self, leader: Union[LeaderModel, AdminModel], date: datetime) -> bool:
        # NOTE: The same condition as on update
        return await self.canUpdateCrew(leader, date)
    

    @transaction
    @typechecked
    async def deleteCrew(self, leader: Union[LeaderModel, AdminModel], date: datetime, session: AsyncSession) -> None:

        if not await self.canDeleteCrew(leader, date, session=session): 
            raise RepositoryPermissionError(f"{leader.display_user_name()} is not able to update crew {leader.crewId}")

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


    @session
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
    
    @session
    @typechecked
    async def queryTeamData(self, member: MemberModel, date: datetime, session: AsyncSession) -> TeamData:

        teamId: Final[int] = member.teamId

        # Detect member status
        is_member: Final[bool] = await self.__checkMemberTeam(member, session= session)
        is_admin: Final[bool] = await self.__checkAdminTeam(member.combineId(AdminModel, teamId), session= session)

        # Query team definition
        teamEntity: Final[Team] = await self.__queryTeam(teamId, session= session)

        def make_mate_data_list(mates: Iterable[Member]) -> List[MemberData]:
            return [MemberData.model_validate(mate) for mate in mates]

        async def make_crew_data(crew: Crew) -> CrewData:
            # Query crew leader
            is_leader = await self.__checkLeaderCrew(member.combineId(LeaderModel, crew.id))

            # Query mates of crew
            query = select(Member).where(Member.crewId == crew.id).order_by(Member.position)
            mates = make_mate_data_list((await session.execute(query)).scalars())

            return CrewData(
                is_admin=is_admin,
                is_leader=is_leader,
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

        # Compute deadline days
        deadline_days_left=(teamEntity.deadline - date).days if teamEntity.deadline is not None else None

        # build team summary
        return TeamData(
            is_admin=is_admin,
            is_member=is_member,
            can_insert_member=await self.canInsertTeamMember(member=member, date=date, session=session),
            can_remove_member=await self.canRemoveTeamMember(member=member, date=date, session=session),
            can_insert_crew=await self.canInsertCrew(person=member, date=date, session=session),
            deadline_days_left=deadline_days_left,
            crews=await make_crew_data_list(crews),
            outboards=make_mate_data_list(outboards),
            **TeamModel.model_validate(teamEntity).model_dump()
           )
