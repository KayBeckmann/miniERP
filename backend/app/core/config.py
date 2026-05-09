from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    DATABASE_URL: str
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    FIRST_SUPERUSER_EMAIL: str
    FIRST_SUPERUSER_PASSWORD: str

    OLLAMA_URL: str = "http://ollama:11434"
    GOTENBERG_URL: str = "http://gotenberg:3000"
    PAPERLESS_URL: str = "http://localhost:8000"
    PAPERLESS_TOKEN: str = ""

    DEBUG: bool = False


settings = Settings()
