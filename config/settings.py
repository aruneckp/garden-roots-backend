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

    # ── Oracle Wallet (required for Oracle Autonomous Database / cloud) ───────
    # Store each file separately to stay under Railway's 32 KB env var limit.
    oracle_ewallet_pem_b64: str = ""   # base64 of ewallet.pem (oracledb thin mode needs PEM not P12)
    oracle_wallet_password: str = ""   # wallet password from OCI download dialog
    oracle_tnsnames: str = ""          # full text of tnsnames.ora
    oracle_sqlnet: str = ""            # full text of sqlnet.ora

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



settings = Settings()
