from pydantic import ConfigDict
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str
    WORKER_TICK_SEC: int = 10

    model_config = ConfigDict(env_file=".env")


settings = Settings()
