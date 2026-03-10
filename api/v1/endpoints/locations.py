from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List

from database.connection import get_db
from database.models import Location
from schemas.location import LocationOut
from schemas.common import APIResponse

router = APIRouter(prefix="/locations", tags=["locations"])


@router.get("", response_model=APIResponse[List[LocationOut]])
def list_locations(db: Session = Depends(get_db)):
    """Return all pickup locations."""
    locations = db.query(Location).order_by(Location.id).all()
    data = [LocationOut.model_validate(loc) for loc in locations]
    return APIResponse(data=data)
