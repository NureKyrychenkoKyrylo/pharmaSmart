from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "PharmaSmart API"
    VERSION: str = "1.0.0"
    
    DATABASE_URL: str = (
        "postgresql://neondb_owner:"
        "npg_kBYo5QdEp8xX"
        "@ep-royal-flower-ageqyrt3-pooler.c-2.eu-central-1.aws.neon.tech/"
        "neondb"
    )

    SECRET_KEY: str = "09d25e094faa6ca2556c818166b7a9563b93f7099f6f0f4caa6cf63b88e8d3e7"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    class Config:
        env_file = ".env"

settings = Settings()
