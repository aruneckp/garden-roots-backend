from typing import List
from urllib.parse import quote_plus
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

    # Cloud ATP wallet — all three required together for wallet mode
    db_tns_name: str = ""         # TNS alias e.g. gardenroots2026_tp
    db_wallet_path: str = ""      # absolute path to wallet dir
    db_wallet_password: str = ""  # password set when downloading wallet from OCI

    # Cloud ATP thin mode — no wallet needed (mTLS must be disabled in OCI console)
    db_dsn: str = ""              # full TCPS connection string from OCI console

    # Local XE only (not used when wallet or dsn is configured)
    db_host: str = "localhost"
    db_port: int = 1521
    db_service: str = "XEPDB1"

    # ── FastAPI ───────────────────────────────────────────────────────────────
    api_title: str = "Garden Roots API"
    api_version: str = "1.0.0"
    debug: bool = False

    # ── CORS ─────────────────────────────────────────────────────────────────
    allowed_origins: List[str] = ["http://localhost:5173", "http://localhost:3000"]

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

    @property
    def use_wallet(self) -> bool:
        return bool(self.db_wallet_path and self.db_tns_name)

    @property
    def use_dsn(self) -> bool:
        return bool(self.db_dsn)

    @property
    def db_connection_string(self) -> str:
        user = quote_plus(self.db_user)
        pw = quote_plus(self.db_password)
        if self.use_wallet or self.use_dsn:
            # Bare URL — DSN/TNS supplied via connect_args
            return f"oracle+oracledb://{user}:{pw}@"
        # Local XE — standard TCP
        return (
            f"oracle+oracledb://{user}:{pw}"
            f"@{self.db_host}:{self.db_port}/?service_name={self.db_service}"
        )

    @property
    def db_connect_args(self) -> dict:
        if self.use_wallet:
            return {
                "dsn": self.db_tns_name,
                "config_dir": self.db_wallet_path,
                "wallet_location": self.db_wallet_path,
                "wallet_password": self.db_wallet_password,
            }
        if self.use_dsn:
            return {"dsn": self.db_dsn}
        return {}


settings = Settings()
