from pydantic import BaseModel

class SkillCreate(BaseModel):
    name: str