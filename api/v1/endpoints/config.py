from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from database.connection import get_db
from database.models import SiteConfig
from schemas.config import SiteConfigOut, SiteConfigUpdate, SiteConfigMapOut
from schemas.common import APIResponse
from utils.auth import get_current_admin

router = APIRouter(prefix="/config", tags=["config"])


@router.get("", response_model=APIResponse[SiteConfigMapOut])
def get_config(db: Session = Depends(get_db)):
    """Return site config as a flat map. Public endpoint."""
    rows = db.query(SiteConfig).all()
    data = {r.config_key: r.config_value for r in rows}
    return APIResponse(data=SiteConfigMapOut(
        banner_messages=data.get("banner_messages"),
        banner_statuses=data.get("banner_statuses"),
        uploaded_banners=data.get("uploaded_banners"),
        self_collection_common_message=data.get("self_collection_common_message"),
    ))


@router.patch("/{config_key}", response_model=APIResponse[SiteConfigOut])
def update_config(
    config_key: str,
    body: SiteConfigUpdate,
    db: Session = Depends(get_db),
    _admin=Depends(get_current_admin),
):
    """Update a config value. Requires admin auth."""
    # Use Oracle MERGE to atomically insert-or-update without touching the
    # GENERATED ALWAYS AS IDENTITY column (ORM INSERT would fail on first save).
    db.execute(
        text("""
            MERGE INTO site_config sc
            USING (SELECT :ck AS config_key FROM DUAL) src
            ON (sc.config_key = src.config_key)
            WHEN MATCHED THEN
                UPDATE SET sc.config_value = :cv,
                           sc.updated_at   = SYSTIMESTAMP
            WHEN NOT MATCHED THEN
                INSERT (config_key, config_value)
                VALUES (:ck, :cv)
        """),
        {"ck": config_key, "cv": body.config_value},
    )
    db.commit()
    row = db.query(SiteConfig).filter(SiteConfig.config_key == config_key).first()
    if not row:
        raise HTTPException(status_code=500, detail="Config key not found after save")
    return APIResponse(data=SiteConfigOut.model_validate(row))
