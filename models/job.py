from pydantic import BaseModel

class JobCreate(BaseModel):
    title: str
    description: str
    district: str
    ds: str
    employer_nic: str