"""
Database handler

@Author: Denis Maydykovsky
"""

import logging

from contextlib import asynccontextmanager
from typeguard import typechecked
from sqlalchemy.engine import Engine
from sqlalchemy.event import listens_for
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from typing import AsyncContextManager, AsyncIterator

_logger = logging.getLogger(__name__)   

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


class Connection:
    """
    Database connection handler
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

    @typechecked
    def make_session(self, commit: bool) -> AsyncContextManager[AsyncSession]:
        if commit:
            return self.session_maker.begin()
        else:
            return self.session_maker()
        
    
@asynccontextmanager
async def create_connection(db_path: str) -> AsyncIterator[Connection]:
    connection = Connection(db_path)
    yield connection
    await connection.close()

