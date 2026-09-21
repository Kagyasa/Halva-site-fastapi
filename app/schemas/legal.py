from datetime import datetime

from pydantic import BaseModel, ConfigDict


class PrivacyPolicySchema(BaseModel):
    id: str
    version: str
    title: str
    text: str
    content_sha256: str
    published_at: datetime | None

    model_config = ConfigDict(from_attributes=True)


class ConsentTextSchema(BaseModel):
    id: str
    version: str
    text: str
    content_sha256: str
    published_at: datetime | None

    model_config = ConfigDict(from_attributes=True)