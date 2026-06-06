from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    BASE_URL: str
    DATABASE_URL: str
    POSTGRES_HOST: str
    POSTGRES_USER: str
    POSTGRES_PORT: str
    POSTGRES_DB: str
    POSTGRES_PASSWORD: str

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore"
    )


env = Settings()