from pydantic import BaseModel

class UserCreate(BaseModel):
    nic: str
    first_name: str
    last_name: str
    phone: str
    language: str
    district: str
    ds_area: str
    pin: str


class UserLogin(BaseModel):
    nic: str
    pin: str


class UserUpdate(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    phone: str | None = None
    language: str | None = None
    district: str | None = None
    ds_area: str | None = None
    pin: str | None = None
    role: str | None = None