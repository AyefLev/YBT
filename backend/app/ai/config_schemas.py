from datetime import datetime

from pydantic import BaseModel, Field


class AIProviderConfigRead(BaseModel):
    role: str
    base_url: str
    model: str
    prompt_price_per_1k: float = 0.0
    completion_price_per_1k: float = 0.0
    currency: str = "CNY"
    enabled: bool
    api_key_configured: bool
    api_key_preview: str = ""
    updated_at: datetime | None = None


class AIProviderConfigUpdate(BaseModel):
    base_url: str | None = Field(default=None, max_length=1024)
    api_key: str | None = None
    clear_api_key: bool = False
    model: str | None = Field(default=None, max_length=255)
    prompt_price_per_1k: float | None = Field(default=None, ge=0)
    completion_price_per_1k: float | None = Field(default=None, ge=0)
    currency: str | None = Field(default=None, max_length=16)
    enabled: bool | None = None
