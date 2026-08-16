from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import desc, asc

try:
    from backend.db.database import get_db
    from backend.models.incident import Incident, NeedType, IncidentStatus
    from backend.schemas.incident import (
        IncidentCreate,
        IncidentResponse,
        IncidentStatusUpdate,
    )
    from backend.services.claude_service import extract_triage_data
    from backend.services.heuristics import apply_severity_heuristics, apply_severity_heuristics_with_details
except ImportError:
    from db.database import get_db
    from models.incident import Incident, NeedType, IncidentStatus
    from schemas.incident import (
        IncidentCreate,
        IncidentResponse,
        IncidentStatusUpdate,
    )
    from services.claude_service import extract_triage_data
    from services.heuristics import apply_severity_heuristics, apply_severity_heuristics_with_details

router = APIRouter(prefix="/incidents", tags=["Incidents"])

# Define strict forward-only progression order
STATUS_ORDER = {
    IncidentStatus.NEW: 0,
    IncidentStatus.ACKNOWLEDGED: 1,
    IncidentStatus.DISPATCHED: 2,
    IncidentStatus.RESOLVED: 3,
}


@router.post("", response_model=IncidentResponse, status_code=status.HTTP_201_CREATED)
def create_incident(
    payload: IncidentCreate,
    db: Session = Depends(get_db)
):
    """
    Intake a raw distress message in any regional language.
    1. Extracts structured triage data using Claude (Sonnet 4.5).
    2. Applies explainable keyword-heuristic severity boost.
    3. Persists the incident to SQLite and returns the full record.
    """
    raw_text = payload.text.strip()
    if not raw_text:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Distress text cannot be empty."
        )

    # 1. Claude extraction (raises 502 with structured error if parsing fails)
    extracted = extract_triage_data(raw_text)

    # 2. Heuristic severity adjustment
    llm_severity = extracted.get("severity", 3)
    translated_text = extracted.get("translated_text", "")
    
    final_severity, matched_keywords = apply_severity_heuristics_with_details(
        original_text=raw_text,
        translated_text=translated_text,
        llm_severity=llm_severity
    )

    print("\n" + "=" * 60)
    print("--- RAW CLAUDE EXTRACTION (BEFORE HEURISTIC BOOST) ---")
    print(f"Original Language: {extracted.get('original_language')}")
    print(f"Translated Text:   {translated_text}")
    print(f"Location:          {extracted.get('location')}")
    print(f"LLM Base Severity: {llm_severity} / 5")
    print(f"Need Type:         {extracted.get('need_type')}")
    print(f"People Affected:   {extracted.get('people_affected')}")
    print(f"Summary:           {extracted.get('summary')}")
    print(f"Confidence:        {extracted.get('confidence')}")
    print("--- HEURISTIC BOOST ENGINE ---")
    print(f"Matched Keywords:  {matched_keywords if matched_keywords else 'None'}")
    print(f"Boost Applied:     +{len(matched_keywords)} (Capped at 5)")
    print(f"Final Severity:    {final_severity} / 5")
    print("=" * 60 + "\n")

    # Ensure need_type maps to valid enum
    need_type_val = extracted.get("need_type", "other").lower()
    try:
        need_type_enum = NeedType(need_type_val)
    except ValueError:
        need_type_enum = NeedType.OTHER

    # 3. Create ORM record
    incident = Incident(
        original_language=extracted.get("original_language", "Unknown"),
        original_text=raw_text,
        translated_text=translated_text,
        location=extracted.get("location"),
        severity=final_severity,
        need_type=need_type_enum,
        people_affected=extracted.get("people_affected"),
        summary=extracted.get("summary", "")[:255],
        confidence=extracted.get("confidence", 0.0),
        status=IncidentStatus.NEW
    )

    db.add(incident)
    db.commit()
    db.refresh(incident)

    return incident


@router.get("", response_model=List[IncidentResponse])
def list_incidents(
    status: Optional[IncidentStatus] = Query(None, description="Filter by incident status"),
    need_type: Optional[NeedType] = Query(None, description="Filter by need type"),
    db: Session = Depends(get_db)
):
    """
    List all incidents, sorted by severity DESC, then created_at ASC.
    Supports filtering by ?status= and ?need_type=.
    """
    query = db.query(Incident)

    if status is not None:
        query = query.filter(Incident.status == status)

    if need_type is not None:
        query = query.filter(Incident.need_type == need_type)

    incidents = query.order_by(
        desc(Incident.severity),
        asc(Incident.created_at)
    ).all()

    return incidents


@router.get("/{incident_id}", response_model=IncidentResponse)
def get_incident(
    incident_id: int,
    db: Session = Depends(get_db)
):
    """
    Retrieve a single incident by ID.
    """
    incident = db.query(Incident).filter(Incident.id == incident_id).first()
    if not incident:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Incident with ID {incident_id} not found."
        )
    return incident


@router.patch("/{incident_id}/status", response_model=IncidentResponse)
def update_incident_status(
    incident_id: int,
    payload: IncidentStatusUpdate,
    db: Session = Depends(get_db)
):
    """
    Update incident status following forward-only lifecycle:
    new -> acknowledged -> dispatched -> resolved
    """
    incident = db.query(Incident).filter(Incident.id == incident_id).first()
    if not incident:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Incident with ID {incident_id} not found."
        )

    current_status = incident.status
    target_status = payload.status

    current_order = STATUS_ORDER.get(current_status, 0)
    target_order = STATUS_ORDER.get(target_status, 0)

    # Validate forward-only transition
    if target_order <= current_order:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Invalid status transition from '{current_status.value}' to '{target_status.value}'. "
                f"Status transitions must progress forward: new -> acknowledged -> dispatched -> resolved."
            )
        )

    incident.status = target_status
    db.commit()
    db.refresh(incident)

    return incident
