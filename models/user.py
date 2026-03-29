from pydantic import BaseModel

class UserCreate(BaseModel):
    nic: str
    first_name: str
    last_name: str
    phone: str
    language: str