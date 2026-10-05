from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):

    database_url: str
    # jwt_token_expiration: int
    # secret_key: str
    # debug: bool

    model_config = SettingsConfigDict(
        env_file=".env"
    )


settings = Settings()
