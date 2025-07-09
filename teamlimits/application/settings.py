"""
Module settings
Extract settings from the file .env or environment.
NOTE: Don't save the TOKEN in the code!

@Author: Denis Maydykovsky
"""


from pydantic import computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class Settings(BaseSettings):
    TOKEN: str
    SQLITE_DB_PATH: Optional[str] = None

    model_config = SettingsConfigDict(env_prefix="TEAMLIMITSBOT_", env_file="config/.env")

    @computed_field
    @property
    def db_url(self) -> str:
        if self.SQLITE_DB_PATH :
            return f"sqlite+aiosqlite:///{self.SQLITE_DB_PATH}"
        else:
            raise RuntimeError("Database path or connection is not specified.")
    