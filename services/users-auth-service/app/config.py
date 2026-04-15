from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    service_name: str = "users-auth-service"
    http_port: int = 8000
    grpc_port: int = 50051

    secret_key: str = Field(default="change-this-in-production", min_length=16)
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60

    database_url: str = "postgresql+psycopg://groupsapp:groupsapp@users-auth-db:5432/users_auth"
    amqp_url: str = "amqp://guest:guest@rabbitmq:5672/"
    consul_url: str = "http://consul:8500"


@lru_cache
def get_settings() -> Settings:
    return Settings()
