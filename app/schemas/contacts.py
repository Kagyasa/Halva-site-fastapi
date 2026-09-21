from pydantic import BaseModel, ConfigDict


class SiteContactResponse(BaseModel):
    id: str
    type: str
    title: str
    value: str

    model_config = ConfigDict(from_attributes=True)
