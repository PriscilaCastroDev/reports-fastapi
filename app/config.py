from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    db_host: str = "localhost"
    db_port: int = 8123  # ClickHouse HTTP port
    db_name: str = "xdr"
    db_user: str = "reports_user"
    db_password: str = ""

    app_host: str = "0.0.0.0"
    app_port: int = 4002
    log_level: str = "INFO"

    max_rows_sync: int = 100_000

    @property
    def database_url(self) -> str:
        return (
            f"clickhouse+connect://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )


settings = Settings()

if __name__ == "__main__":
    print(f"Host: {settings.db_host}")
    print(f"User: {settings.db_user}")
    print(f"DB:   {settings.db_name}")