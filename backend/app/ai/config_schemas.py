from datetime import datetime

from pydantic import BaseModel, Field


class AIProviderConfigRead(BaseModel):
    role: str
    base_url: str
    model: str
    enabled: bool
    api_key_configured: bool
    api_key_preview: str = ""
    updated_at: datetime | None = None


class AIProviderConfigUpdate(BaseModel):
    base_url: str | None = Field(default=None, max_length=1024)
    api_key: str | None = None
    clear_api_key: bool = False
    model: str | None = Field(default=None, max_length=255)
    enabled: bool | None = None
