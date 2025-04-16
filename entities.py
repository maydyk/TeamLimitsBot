"""
Define database entities

1) Update database schema:
.venv/bin/alembic revision --autogenerate -m "Revision name"
2) Apply changes:
.venv/bin/alembic upgrade head

@Author: Denis Maydykovsky
"""

import re

from datetime import datetime
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
from sqlalchemy.orm import DeclarativeBase, declared_attr, Mapped, mapped_column, class_mapper
from sqlalchemy.ext.asyncio import AsyncAttrs
from typing import Any, Dict, Final, Optional

def camel_to_snake(text: str) -> str:
    """
    Convert CamelCase string to snake_case string.
    """
    
    # See https://sky.pro/wiki/python/preobrazovanie-camel-case-v-snake-case-v-python-funktsiya/
    return re.sub(r"(?<!^)(?=[A-Z])", "_", text)


class Entity(AsyncAttrs, DeclarativeBase):
    """
    Common entity
    """

    # Don't create table for this class
    __abstract__ = True

    # Common columns
    createdAt: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
    )

    updatedAt: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    def to_dict(self) -> dict:
        """
        Get dictionary for given entity.
        """
        # Get the mapper
        columns = class_mapper(self.__class__).columns
        # Make dictionary from column names and their values
        return {column.key: getattr(self, column.key) for column in columns}


    # Build table name from class name
    @declared_attr.directive
    def __tablename__(cls) -> str:
        return f"{camel_to_snake(cls.__name__).upper()}S"



class Team(Entity):
    
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(unique=True, nullable=False)
    description: Mapped[str]
    minimalMembers: Mapped[int] = mapped_column()
    maximalMembers: Mapped[int] = mapped_column()
    enableCrews: Mapped[bool]
    minimalCrews: Mapped[int] = mapped_column()
    maximalCrews: Mapped[int] = mapped_column()
    deadline: Mapped[Optional[datetime]]
    suspendCompanions: Mapped[bool] = mapped_column(server_default="0")
    suspendRecruitment: Mapped[bool]
    suspendPendingQueue: Mapped[bool]
    suspendDeadlineQueue: Mapped[bool]

    __table_args__ = (
        CheckConstraint(title != '', name="title_is_not_empty"),
        CheckConstraint(minimalMembers <= maximalMembers, name="min_max_members"),
        CheckConstraint(minimalCrews <= maximalCrews, name="min_max_crews"),
    )


class Crew(Entity):

    _DEFAULT_CREW_SPECIAL: Final[int] = 1

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    teamId: Mapped[int] = mapped_column(
        ForeignKey(Team.id, ondelete="CASCADE"),
        nullable=False,
    )
    title: Mapped[str] = mapped_column()
    minimalMates: Mapped[int] = mapped_column()
    maximalMates: Mapped[int] = mapped_column()
    special: Mapped[int] = mapped_column()

    # Crew title must be unique in the crew. 
    __table_args__ = (
        UniqueConstraint(teamId, title, special), 
        CheckConstraint((special != 0) or (title != ''), name="special_title"),
        CheckConstraint(minimalMates <= maximalMates, name="min_max_mates"),
    )
    

# Telegram doesn't allow retrieve user name etc by ID. We have to store all user info every time.
class Person(Entity):
    # Don't create table for this class
    __abstract__ = True

    # NOTE: Alembic cannot use the names of abstract base classes 
    USER_ID: Final[str] = "userId"
    USER_NAME: Final[str] = "userName"

    userId: Mapped[int] = mapped_column(Integer, name=USER_ID)
    userName: Mapped[str] = mapped_column(String, name=USER_NAME)
    firstName: Mapped[str] = mapped_column(String)
    lastName: Mapped[str] = mapped_column(String)


class Member(Person):

    number: Mapped[int] = mapped_column()
    teamId: Mapped[int] = mapped_column(ForeignKey(Team.id, ondelete="CASCADE"))
    crewId: Mapped[Optional[int]] = mapped_column(ForeignKey(Crew.id, ondelete="SET NULL"))
    position: Mapped[int] = mapped_column()

    __table_args__ = (
        PrimaryKeyConstraint(Person.USER_ID, Person.USER_NAME, number, teamId),
        UniqueConstraint(Person.USER_ID, Person.USER_NAME, number, teamId, position, name="UniqueMember"),
    )


class Outcast(Person):
    teamId: Mapped[int] = mapped_column(ForeignKey(Team.id, ondelete="CASCADE"))

    __table_args__ = (PrimaryKeyConstraint(Person.USER_ID, Person.USER_NAME, teamId), )


class Leader(Person):
    crewId: Mapped[int] = mapped_column(ForeignKey(Crew.id, ondelete="CASCADE"))

    __table_args__ = (PrimaryKeyConstraint(Person.USER_ID, Person.USER_NAME, crewId), )


class Admin(Person):
    teamId: Mapped[int] = mapped_column(ForeignKey(Team.id, ondelete="CASCADE"))

    __table_args__ = (PrimaryKeyConstraint(Person.USER_ID, Person.USER_NAME, teamId), )


# Self testing
if __name__ == "__main":

    # Testing camel_to_snake
    assert(camel_to_snake("ClassObjectX").lower() == "class_object_x")
