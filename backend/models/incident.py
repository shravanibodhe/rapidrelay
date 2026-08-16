import enum
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, Float, DateTime, Enum

try:
    from backend.db.database import Base
except ImportError:
    from db.database import Base


class NeedType(str, enum.Enum):
    MEDICAL = "medical"
    RESCUE = "rescue"
    FOOD = "food"
    WATER = "water"
    SHELTER = "shelter"
    OTHER = "other"


class IncidentStatus(str, enum.Enum):
    NEW = "new"
    ACKNOWLEDGED = "acknowledged"
    DISPATCHED = "dispatched"
    RESOLVED = "resolved"


class Incident(Base):
    __tablename__ = "incidents"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    original_language = Column(String(50), nullable=False)
    original_text = Column(Text, nullable=False)
    translated_text = Column(Text, nullable=False)
    location = Column(String(255), nullable=True)
    severity = Column(Integer, nullable=False, default=1)
    need_type = Column(
        Enum(NeedType, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        default=NeedType.OTHER
    )
    people_affected = Column(Integer, nullable=True)
    summary = Column(String(255), nullable=False)
    confidence = Column(Float, nullable=False, default=0.0)
    status = Column(
        Enum(IncidentStatus, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        default=IncidentStatus.NEW
    )

    def __repr__(self):
        return f"<Incident(id={self.id}, severity={self.severity}, need_type='{self.need_type}', status='{self.status}')>"
