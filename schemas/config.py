from pydantic import BaseModel, ConfigDict
from typing import Optional, List


class SiteConfigOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    config_key: str
    config_value: Optional[str] = None
    description: Optional[str] = None


class SiteConfigUpdate(BaseModel):
    config_value: str


class SiteConfigMapOut(BaseModel):
    banner_messages: Optional[str] = None
