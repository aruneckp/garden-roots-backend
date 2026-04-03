import json
from typing import List
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Oracle Database ───────────────────────────────────────────────────────
    db_user: str
    db_password: str

    # Local XE (no wallet needed)
    db_host: str = "localhost"
    db_port: int = 1521
    db_service: str = "XEPDB1"

    # Cloud ADB — wallet files stored as env vars (base64/text), written to
    # a temp dir at startup by database/connection.py
    oracle_ewallet_pem_b64: str = ""   # base64 of ewallet.pem
    oracle_wallet_password: str = ""   # wallet password from OCI
    oracle_tnsnames: str = ""          # full text of tnsnames.ora
    oracle_sqlnet: str = ""            # full text of sqlnet.ora

    # ── FastAPI ───────────────────────────────────────────────────────────────
    api_title: str = "Garden Roots API"
    api_version: str = "1.0.0"
    debug: bool = False

    # ── CORS ─────────────────────────────────────────────────────────────────
    # Accepts JSON array or comma-separated string from Render env vars
    allowed_origins: List[str] = ["http://localhost:5173", "http://localhost:3000"]

    @field_validator("allowed_origins", mode="before")
    @classmethod
    def parse_origins(cls, v):
        if isinstance(v, str):
            v = v.strip()
            if v.startswith("["):
                return json.loads(v)
            return [o.strip() for o in v.split(",") if o.strip()]
        return v

    # ── URLs ─────────────────────────────────────────────────────────────────
    app_url: str = "http://localhost:8000"
    frontend_url: str = "http://localhost:5173"

    # ── HitPay ────────────────────────────────────────────────────────────────
    hitpay_api_key: str = ""
    hitpay_salt: str = ""
    hitpay_is_sandbox: bool = True

    # ── Stripe ────────────────────────────────────────────────────────────────
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""

    # ── Google OAuth ──────────────────────────────────────────────────────────
    google_client_id: str = ""
    google_client_secret: str = ""

    # ── Business rules ────────────────────────────────────────────────────────
    delivery_free_threshold: float = 120.0
    delivery_cost: float = 12.0


settings = Settings()
