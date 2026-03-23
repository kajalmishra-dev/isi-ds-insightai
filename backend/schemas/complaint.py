from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class ComplaintRequest(BaseModel):
    text: str

class ComplaintResponse(BaseModel):
    text: str
    category: Optional[str]
    confidence: Optional[float]
    created_at: datetime
    resolved_at: Optional[datetime]

    class Config:
        from_attributes = True