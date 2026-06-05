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

    # Scheduler — persistencia SQLite (relativa para dev; en contenedor se monta /app/data)
    sqlite_path: str = "data/schedules.db"

    # Scheduler — zona horaria para interpretar hour/minute de los schedules.
    # El contenedor corre en UTC; sin esto los jobs se disparan con el offset corrido.
    scheduler_timezone: str = "America/Mexico_City"

    # Scheduler — SMTP (Gmail). En prod, SMTP_PASSWORD es un App Password de 16 chars.
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""

    cors_origins: str = "http://localhost:3001"

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

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