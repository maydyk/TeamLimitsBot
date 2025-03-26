"""
Define database entities

1) Update database schema .venv/bin/alembic revision --autogenerate -m "Revision name"
2) Apply changes: .venv/bin/alembic upgrade head

@Author: Denis Maydykovsky
"""

from datetime import datetime
from operator import itemgetter
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Integer,
    func,
    PrimaryKeyConstraint,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, declared_attr, Mapped, mapped_column
from sqlalchemy.ext.asyncio import AsyncAttrs
from typing import Any, Dict, Final

from details import camel_to_snake, even_hex

class Entity(AsyncAttrs, DeclarativeBase):
    """
    Common entity
    """
    CREATED_AT: Final[str] = "createdAt"
    UPDATED_AT: Final[str] = "updatedAt"

    # Don't create table for this class
    __abstract__ = True

    # Common columns
    createdAt: Mapped[datetime] = mapped_column(
        DateTime,
        name=CREATED_AT,
        nullable=False,
        server_default=func.now(),
    )

    updatedAt: Mapped[datetime] = mapped_column(
        DateTime,
        name=UPDATED_AT,
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    # Build table name from class name
    @declared_attr.directive
    def __tablename__(cls) -> str:
        return f"{camel_to_snake(cls.__name__).upper()}S"


class Team(Entity):
    ID: Final[str] = "id"
    TITLE: Final[str] = "title"
    DESCRIPTION: Final[str] = "description"
    MINIMAL_MEMBERS: Final[str] = "minimalMembers"
    MAXIMAL_MEMBERS: Final[str] = "maximalMembers"
    ENABLE_CREWS: Final[str] = "enableCrews"
    RESTRICT_CREWS: Final[str] = "restrictCrews"
    MINIMAL_CREWS: Final[str] = "minimalCrews"
    MAXIMAL_CREWS: Final[str] = "maximalCrews"
    ENABLE_DEADLINE: Final[str] = "enableDeadline"
    DEADLINE: Final[str] = "deadline"
    SUSPEND_RECRUITMENT: Final[str] = "suspendRecruitment"
    SUSPEND_PENDING_QUEUE: Final[str] = "suspendPendingQueue"
    SUSPEND_DEADLINE_QUEUE: Final[str] = "suspendDeadlineQueue"
    
    id: Mapped[int] = mapped_column(Integer, name=ID, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String, name=TITLE, unique=True, nullable=False)
    description: Mapped[str] = mapped_column(String, name=DESCRIPTION, nullable=False, server_default="")
    minimalMembers: Mapped[int] = mapped_column(Integer, name=MINIMAL_MEMBERS, nullable=False, server_default="0")
    maximalMembers: Mapped[int] = mapped_column(Integer, name=MAXIMAL_MEMBERS, nullable=False, server_default="0")
    enableCrews: Mapped[bool] = mapped_column(Boolean, name=ENABLE_CREWS, nullable=False, server_default="0")
    restrictCrews: Mapped[bool] = mapped_column(Boolean, name=RESTRICT_CREWS, nullable=False, server_default="0")
    minimalCrews: Mapped[int] = mapped_column(Integer, name=MINIMAL_CREWS, nullable=False, server_default="0")
    maximalCrews: Mapped[int] = mapped_column(Integer, name=MAXIMAL_CREWS, nullable=False, server_default="0")
    enableDeadline: Mapped[int] = mapped_column(Boolean, name=ENABLE_DEADLINE, nullable=False,server_default="0")
    deadline: Mapped[datetime] = mapped_column(DateTime, name=DEADLINE, nullable=True, server_default=None)
    suspendRecruitment: Mapped[bool] = mapped_column(Boolean, name=SUSPEND_RECRUITMENT, nullable=False, server_default="0")
    suspendPendingQueue: Mapped[bool] = mapped_column(Boolean, name=SUSPEND_PENDING_QUEUE, nullable=False, server_default="0")
    suspendDeadlineQueue: Mapped[bool] = mapped_column(Boolean, name=SUSPEND_DEADLINE_QUEUE, nullable=False, server_default="0")

    __table_args__ = (
        CheckConstraint(f"{TITLE} != ''"),
        CheckConstraint(f"{MINIMAL_MEMBERS} <= {MAXIMAL_MEMBERS}"),
        CheckConstraint(f"{MINIMAL_CREWS} <= {MAXIMAL_CREWS}"),
        )

    @staticmethod
    def id_key() -> str:
        """
        Build the reference to 'id' to use as foreign key
        """
        return f"{Team.__tablename__}.{Team.ID}"
    
    def as_dict(self) -> Dict[str, Any]:
        """
        Represent Team values as dictionary
        """
        return {
            Team.ID                    : self.id,
            Team.TITLE                 : self.title,
            Team.DESCRIPTION           : self.description,
            Team.MINIMAL_MEMBERS       : self.minimalMembers,
            Team.MAXIMAL_MEMBERS       : self.maximalMembers,
            Team.ENABLE_CREWS          : self.enableCrews,
            Team.RESTRICT_CREWS        : self.restrictCrews,
            Team.MINIMAL_CREWS         : self.minimalCrews,
            Team.MAXIMAL_CREWS         : self.maximalCrews,
            Team.ENABLE_DEADLINE       : self.enableDeadline,
            Team.DEADLINE              : self.deadline,
            Team.SUSPEND_RECRUITMENT   : self.suspendRecruitment,
            Team.SUSPEND_PENDING_QUEUE : self.suspendPendingQueue,
            Team.SUSPEND_DEADLINE_QUEUE: self.suspendDeadlineQueue, 
        }
    
    @staticmethod
    def clean_dict(**values) -> Dict[str, Any]:
        """
        Remove from values non-Team values.
        """
        keys = (
            Team.ID,
            Team.TITLE,
            Team.DESCRIPTION,
            Team.MINIMAL_MEMBERS,
            Team.MAXIMAL_MEMBERS,
            Team.ENABLE_CREWS,
            Team.RESTRICT_CREWS,
            Team.MINIMAL_CREWS,
            Team.MAXIMAL_CREWS,
            Team.ENABLE_DEADLINE,
            Team.DEADLINE,
            Team.SUSPEND_RECRUITMENT,
            Team.SUSPEND_PENDING_QUEUE,
            Team.SUSPEND_DEADLINE_QUEUE,
        )
        return dict(zip(keys, itemgetter(*keys)(values)))


class Crew(Entity):
    ID: Final[str] = "id"
    TEAM_ID: Final[str] = "teamId"
    TITLE: Final[str] = "title"
    MINIMAL_MATES: Final[str] = "minimalMates"
    MAXIMAL_MATES: Final[str] = "maximalMates"
    SPECIAL: Final[str] = "special"

    DEFAULT_CREW_SPECIAL: Final[int] = 1

    id: Mapped[int] = mapped_column(Integer, name=ID, primary_key=True, autoincrement=True)
    teamId: Mapped[int] = mapped_column(
        ForeignKey(Team.id_key(), ondelete="CASCADE"),
        name=TEAM_ID,
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String, name=TITLE)
    minimalMates: Mapped[int] = mapped_column(Integer, name=MINIMAL_MATES, nullable=False, server_default="0")
    maximalMates: Mapped[int] = mapped_column(Integer, name=MAXIMAL_MATES, nullable=False, server_default="0")
    special: Mapped[int] = mapped_column(Integer, name=SPECIAL, nullable=False, server_default="0")

    # Crew title must be unique in the crew. 
    __table_args__ = (
        UniqueConstraint(TEAM_ID, TITLE, SPECIAL), 
        CheckConstraint(f"{SPECIAL} > 0 OR {TITLE} != ''"))

    @staticmethod
    def id_key() -> str:
        """
        Build the reference to ;id
        """
        return f"{Crew.__tablename__}.{Crew.ID}"


class Member(Entity):
    USER_ID: Final[int] = "userId"
    NUMBER: Final[int] = "number"
    TEAM_ID: Final[int] = "teamId"
    CREW_ID: Final[int] = "crewId"
    POSITION: Final[int] = "position"

    userId: Mapped[int] = mapped_column(Integer, name=USER_ID, nullable=False)
    number: Mapped[int] = mapped_column(Integer, name=NUMBER, nullable=False, server_default="0")
    teamId: Mapped[int] = mapped_column(
        ForeignKey(Team.id_key(), ondelete="CASCADE"),
        name=TEAM_ID,
        nullable=False,
        )
    crewId: Mapped[int|None] = mapped_column(
        ForeignKey(Crew.id_key(), ondelete="SET NULL"),
        name=CREW_ID,
        nullable=True,
        server_default=None,
        )
    position: Mapped[int] = mapped_column(Integer, name=POSITION, nullable=False)

    __table_args__ = (
        PrimaryKeyConstraint(USER_ID, NUMBER, TEAM_ID),
        UniqueConstraint(USER_ID, NUMBER, TEAM_ID, POSITION),
    )


class Admin(Entity):
    USER_ID: Final[int] = "userId"
    TEAM_ID: Final[int] = "teamId"

    userId: Mapped[int] = mapped_column(Integer, name=USER_ID, nullable=False)
    teamId: Mapped[int] = mapped_column(
        ForeignKey(Team.id_key(), ondelete="CASCADE"),
            name=TEAM_ID,
            nullable=False,
        )

    __table_args__ = (PrimaryKeyConstraint(USER_ID, TEAM_ID), )


class Leader(Entity):
    USER_ID: Final[int] = "userId"
    CREW_ID: Final[int] = "crewId"

    userId: Mapped[int] = mapped_column(Integer, name=USER_ID, nullable=False)
    crewId: Mapped[int] = mapped_column(
        ForeignKey(Crew.id_key(), ondelete="CASCADE"),
        name=CREW_ID,
        nullable=False,
    )

    __table_args__ = (PrimaryKeyConstraint(USER_ID, CREW_ID), )


