from fastapi import APIRouter, Depends, HTTPException
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
    ))


@router.patch("/{config_key}", response_model=APIResponse[SiteConfigOut])
def update_config(
    config_key: str,
    body: SiteConfigUpdate,
    db: Session = Depends(get_db),
    _admin=Depends(get_current_admin),
):
    """Update a config value. Requires admin auth."""
    row = db.query(SiteConfig).filter(SiteConfig.config_key == config_key).first()
    if not row:
        raise HTTPException(status_code=404, detail=f"Config key '{config_key}' not found")
    row.config_value = body.config_value
    db.commit()
    db.refresh(row)
    return APIResponse(data=SiteConfigOut.model_validate(row))
