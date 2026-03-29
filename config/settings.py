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

    # ── HitPay ────────────────────────────────────────────────────────────────
    hitpay_api_key: str = ""          # From HitPay dashboard → Payment Gateway
    hitpay_salt: str = ""             # From HitPay dashboard → Payment Gateway (for webhook HMAC)
    hitpay_is_sandbox: bool = True    # Set False in production
    app_url: str = "http://localhost:8000"        # Backend public URL (for webhook)
    frontend_url: str = "http://localhost:5173"   # Frontend public URL (for redirect_url)

    # ── Google OAuth ──────────────────────────────────────────────────────────
    google_client_id: str = ""

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
