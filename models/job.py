from pydantic import BaseModel

class JobCreate(BaseModel):
    title: str
    description: str
    district: str
    ds_area: str
    employer_nic: str
    location: str | None = None
    date: str | None = None
    time: str | None = None
    skill_codes: list[str] | None = None


class JobStatusUpdate(BaseModel):
    status: str