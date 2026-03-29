from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List
from pydantic import BaseModel, ConfigDict
from typing import Optional

from database.connection import get_db
from database.models import Location, PickupLocation
from schemas.location import LocationOut
from schemas.order import PickupLocationPublicOut
from schemas.common import APIResponse

router = APIRouter(prefix="/locations", tags=["locations"])


@router.get("", response_model=APIResponse[List[LocationOut]])
def list_locations(db: Session = Depends(get_db)):
    """Return all general locations."""
    locations = db.query(Location).order_by(Location.id).all()
    data = [LocationOut.model_validate(loc) for loc in locations]
    return APIResponse(data=data)


@router.get("/pickup", response_model=APIResponse[List[PickupLocationPublicOut]])
def list_pickup_locations(db: Session = Depends(get_db)):
    """Return all active self-pickup locations (for the checkout page)."""
    locations = (
        db.query(PickupLocation)
        .filter(PickupLocation.is_active == 1)
        .order_by(PickupLocation.name)
        .all()
    )
    data = [PickupLocationPublicOut.model_validate(loc) for loc in locations]
    return APIResponse(data=data)
