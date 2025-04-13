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

    model_config = SettingsConfigDict(env_prefix="TEAMLIMITSBOT_", env_file=".env")

    def make_db_url(self) -> str:
        if self.SQLITE_DB_PATH :
            return f"sqlite+aiosqlite:///{self.SQLITE_DB_PATH}"
        else:
            raise RuntimeError("Database path or connection is not specified.")


config = Config()

# Self testing
if __name__ == "__main__":
    print("Config settings\n", config.model_dump())
    


    