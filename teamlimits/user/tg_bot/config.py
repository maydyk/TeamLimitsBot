"""
module config
Extract settings from the file .env or environment.
NOTE: Don't save the TOKEN in the code!

@Author: Denis Maydykovsky
"""


from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Config(BaseSettings):
    TOKEN: str
    SQLITE_DB_PATH: Optional[str] = None

    model_config = SettingsConfigDict(env_prefix="TEAMLIMITSBOT_", env_file="config/.env")

    def make_db_url(self) -> str:
        if self.SQLITE_DB_PATH :
            return f"sqlite+aiosqlite:///{self.SQLITE_DB_PATH}"
        else:
            raise RuntimeError("Database path or connection is not specified.")



# Self testing
if __name__ == "__main__":
    settings = Config()
    print("Config settings\n", settings.model_dump())
    