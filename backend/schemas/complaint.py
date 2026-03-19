from pydantic import BaseModel


class ComplaintRequest(BaseModel):
    text: str


class ComplaintResponse(BaseModel):
    category: str
    confidence: float