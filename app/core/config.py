from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8', extra='ignore')

    app_name: str = 'GroupsApp'
    api_prefix: str = '/api/v1'

    secret_key: str = Field(default='change-this-in-production', min_length=16)
    algorithm: str = 'HS256'
    access_token_expire_minutes: int = 60

    database_url: str = 'sqlite:///./groupsapp.db'
    upload_dir: str = './uploads'


@lru_cache
def get_settings() -> Settings:
    return Settings()
