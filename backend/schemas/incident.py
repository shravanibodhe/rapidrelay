from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict

try:
    from backend.models.incident import NeedType, IncidentStatus
except ImportError:
    from models.incident import NeedType, IncidentStatus


class IncidentCreate(BaseModel):
    text: str = Field(..., min_length=1, description="Raw distress text in any regional language")


class IncidentStatusUpdate(BaseModel):
    status: IncidentStatus = Field(..., description="Target status in forward-only progression")


class TriageExtraction(BaseModel):
    original_language: str
    translated_text: str
    location: Optional[str] = None
    severity: int = Field(..., ge=1, le=5)
    need_type: NeedType
    people_affected: Optional[int] = None
    summary: str
    confidence: float = Field(..., ge=0.0, le=1.0)


class IncidentResponse(BaseModel):
    id: int
    created_at: datetime
    original_language: str
    original_text: str
    translated_text: str
    location: Optional[str]
    severity: int
    need_type: NeedType
    people_affected: Optional[int]
    summary: str
    confidence: float
    status: IncidentStatus

    model_config = ConfigDict(from_attributes=True)
