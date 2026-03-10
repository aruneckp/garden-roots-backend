from pydantic import BaseModel, ConfigDict
from typing import Optional


class LocationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    location_name: str
    address: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    operating_hours: Optional[str] = None
