from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
        extra="ignore",         # ignore unknown env vars — safe for Docker / CI secrets
    )

    # ── Oracle Database ───────────────────────────────────────────────────────
    db_user: str
    db_password: str
    db_host: str
    db_port: int = 1521
    db_service: str

    # ── FastAPI ───────────────────────────────────────────────────────────────
    api_title: str = "Garden Roots API"
    api_version: str = "1.0.0"
    debug: bool = False

    # ── CORS (comma-separated origins in .env are parsed automatically) ───────
    allowed_origins: List[str] = ["http://localhost:5173", "http://localhost:3000"]

    # ── Stripe ────────────────────────────────────────────────────────────────
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""
    app_url: str = "http://localhost:8000"

    # ── Business rules ────────────────────────────────────────────────────────
    delivery_free_threshold: float = 120.0
    delivery_cost: float = 12.0

    @property
    def db_connection_string(self) -> str:
        return (
            f"oracle+oracledb://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/?service_name={self.db_service}"
        )


settings = Settings()
