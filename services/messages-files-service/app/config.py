from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    service_name: str = "messages-files-service"
    http_port: int = 8000

    secret_key: str = Field(default="change-this-in-production", min_length=16)
    algorithm: str = "HS256"

    database_url: str = "postgresql+psycopg://groupsapp:groupsapp@messages-db:5432/messages"
    amqp_url: str = "amqp://guest:guest@rabbitmq:5672/"
    consul_url: str = "http://consul:8500"

    groups_grpc_addr: str = "groups-service:50052"
    users_grpc_addr: str = "users-auth-service:50051"

    # Storage
    storage_backend: str = "local"  # "local" | "s3"
    upload_dir: str = "/data/uploads"
    public_url_base: str = "/uploads"
    s3_bucket: str | None = None
    s3_region: str | None = None


@lru_cache
def get_settings() -> Settings:
    return Settings()
