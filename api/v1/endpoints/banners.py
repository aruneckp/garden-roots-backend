import json
import re
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session

from config.settings import settings
from database.connection import get_db
from database.models import SiteConfig
from schemas.common import APIResponse
from utils.auth import get_current_admin

router = APIRouter(prefix="/admin/banners", tags=["banners"])

ALLOWED_MIME = {
    "image/png", "image/jpeg", "image/webp",
    "image/gif", "image/avif", "image/bmp",
}
ALLOWED_EXT = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".avif", ".bmp"}
MAX_BYTES = 5 * 1024 * 1024  # 5 MB


def _upload_dir() -> Path:
    p = Path(settings.banner_upload_dir)
    if not p.is_absolute():
        p = (Path.cwd() / p).resolve()
    p.mkdir(parents=True, exist_ok=True)
    return p


def _get_uploaded_banners(db: Session) -> list[str]:
    row = db.query(SiteConfig).filter(SiteConfig.config_key == "uploaded_banners").first()
    if not row or not row.config_value:
        return []
    try:
        return json.loads(row.config_value)
    except Exception:
        return []


def _save_uploaded_banners(db: Session, srcs: list[str]) -> None:
    row = db.query(SiteConfig).filter(SiteConfig.config_key == "uploaded_banners").first()
    if row:
        row.config_value = json.dumps(srcs)
    else:
        row = SiteConfig(
            config_key="uploaded_banners",
            config_value=json.dumps(srcs),
            description="JSON array of uploaded banner image src paths.",
        )
        db.add(row)
    db.commit()


@router.post("/upload", response_model=APIResponse[dict])
async def upload_banner(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    _admin=Depends(get_current_admin),
):
    if file.content_type not in ALLOWED_MIME:
        raise HTTPException(400, "Only image files are allowed (png, jpg, webp, gif, avif, bmp).")

    contents = await file.read()
    if len(contents) > MAX_BYTES:
        raise HTTPException(400, "File too large — maximum 5 MB.")

    # Sanitise filename and enforce Banner prefix
    raw = Path(file.filename or "upload.png").name
    safe = re.sub(r"[^\w.\-]", "_", raw)
    ext = Path(safe).suffix.lower()
    if ext not in ALLOWED_EXT:
        raise HTTPException(400, f"Unsupported extension '{ext}'.")
    if not safe.startswith("Banner"):
        safe = f"Banner_{safe}"

    dest = _upload_dir() / safe
    # Avoid clobbering: append _1, _2 … if the file already exists
    if dest.exists():
        stem, i = dest.stem, 1
        while dest.exists():
            dest = _upload_dir() / f"{stem}_{i}{ext}"
            i += 1

    dest.write_bytes(contents)
    src = f"/{dest.name}"

    # Update site_config
    existing = _get_uploaded_banners(db)
    if src not in existing:
        existing.append(src)
    _save_uploaded_banners(db, existing)

    return APIResponse(data={"filename": dest.name, "src": src})


@router.delete("/{filename}", response_model=APIResponse[dict])
def delete_banner(
    filename: str,
    db: Session = Depends(get_db),
    _admin=Depends(get_current_admin),
):
    if not filename.startswith("Banner"):
        raise HTTPException(400, "Only Banner* files can be deleted via this endpoint.")

    dest = _upload_dir() / filename
    if dest.exists():
        dest.unlink()

    src = f"/{filename}"
    existing = [s for s in _get_uploaded_banners(db) if s != src]
    _save_uploaded_banners(db, existing)

    return APIResponse(data={"deleted": filename})
