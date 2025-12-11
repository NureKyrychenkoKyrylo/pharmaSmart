from pydantic_settings import BaseSettings, SettingsConfigDict
import os

class Settings(BaseSettings):
    PROJECT_NAME: str = "PharmaSmart API"
    VERSION: str = "1.0.0"
    
    DATABASE_URL: str
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 120

model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

settings = Settings()
