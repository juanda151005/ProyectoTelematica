from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    service_name: str = "groups-service"
    http_port: int = 8000
    grpc_port: int = 50052

    secret_key: str = Field(default="change-this-in-production", min_length=16)
    algorithm: str = "HS256"

    database_url: str = "postgresql+psycopg://groupsapp:groupsapp@groups-db:5432/groups"
    amqp_url: str = "amqp://guest:guest@rabbitmq:5672/"
    consul_url: str = "http://consul:8500"

    users_grpc_addr: str = "users-auth-service:50051"


@lru_cache
def get_settings() -> Settings:
    return Settings()
