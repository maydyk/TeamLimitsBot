"""
Module application.
General application configuration.
"""
from contextlib import asynccontextmanager
from dependency_injector import containers, providers
from teamlimits.application.settings import Settings 
from teamlimits.database.connection import create_connection
from teamlimits.repository.repository import Repository

class Application(containers.DeclarativeContainer):
    settings = providers.Configuration(pydantic_settings=[Settings()])

    connection = providers.Resource(
        create_connection,
        settings.db_url
    )

    repository = providers.Singleton(
        Repository,
        connection
    )

@asynccontextmanager
async def bound_resources(container: containers.DeclarativeContainer):
    """
    Initialize and shutdown container resources.
    dependency_injector doesn't support Closable for entire container.
    """
    await container.init_resources()
    yield
    await container.shutdown_resources()

