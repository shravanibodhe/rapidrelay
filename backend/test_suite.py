"""
Test Suite for RapidRelay Backend
Verifies heuristics, data models, API endpoints, status state machine, and Claude extraction error handling.
"""

import os
import sys
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from backend.main import app
from backend.services.heuristics import apply_severity_heuristics, apply_severity_heuristics_with_details, SEVERITY_KEYWORDS
from backend.models.incident import IncidentStatus, NeedType
from backend.db.database import Base, engine

client = TestClient(app)


def setup_module():
    Base.metadata.create_all(bind=engine)


def test_severity_heuristics_no_keywords():
    score = apply_severity_heuristics("Everything is calm", "Everything is calm", 2)
    assert score == 2


def test_severity_heuristics_boost_keywords():
    # 'trapped' and 'children' -> +2 boost from base 2 = 4
    score, matches = apply_severity_heuristics_with_details(
        "Children are trapped inside",
        "Children are trapped inside",
        2
    )
    assert score == 4
    assert "trapped" in matches
    assert "children" in matches


def test_severity_heuristics_cap_at_five():
    # Multiple keywords should cap at 5
    score = apply_severity_heuristics(
        "pregnant woman trapped drowning collapsed",
        "pregnant woman trapped drowning collapsed",
        3
    )
    assert score == 5


def test_api_health():
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json()["status"] == "healthy"


def test_get_incidents_list():
    res = client.get("/incidents")
    assert res.status_code == 200
    items = res.json()
    assert isinstance(items, list)
    if len(items) >= 2:
        # Verify sorted by severity DESC
        for i in range(len(items) - 1):
            assert items[i]["severity"] >= items[i+1]["severity"]


def test_get_incidents_filter():
    res = client.get("/incidents?status=new")
    assert res.status_code == 200
    items = res.json()
    for item in items:
        assert item["status"] == "new"


def test_get_single_incident():
    # First get an incident
    res = client.get("/incidents")
    items = res.json()
    assert len(items) > 0
    first_id = items[0]["id"]

    res_single = client.get(f"/incidents/{first_id}")
    assert res_single.status_code == 200
    assert res_single.json()["id"] == first_id

    # 404 for non-existent
    res_404 = client.get("/incidents/999999")
    assert res_404.status_code == 404


def test_status_forward_transition_and_reverse_rejection():
    # Get an incident with status 'new'
    res = client.get("/incidents?status=new")
    items = res.json()
    if not items:
        # If no new incident, list all
        res = client.get("/incidents")
        items = res.json()
    
    target_id = items[0]["id"]
    current_status = items[0]["status"]

    if current_status == "new":
        # Forward transition new -> acknowledged should succeed
        patch_res = client.patch(f"/incidents/{target_id}/status", json={"status": "acknowledged"})
        assert patch_res.status_code == 200
        assert patch_res.json()["status"] == "acknowledged"

        # Reverse transition acknowledged -> new must return 400 Bad Request
        patch_back = client.patch(f"/incidents/{target_id}/status", json={"status": "new"})
        assert patch_back.status_code == 400
        assert "Invalid status transition" in patch_back.json()["detail"]


def test_post_incident_mock_claude():
    mock_claude_response = MagicMock()
    mock_block = MagicMock()
    mock_block.type = "text"
    mock_block.text = """{
      "original_language": "Hindi",
      "translated_text": "Severe flooding in low lying area, families are trapped.",
      "location": "Kankarbagh, Patna",
      "severity": 3,
      "need_type": "rescue",
      "people_affected": 8,
      "summary": "Families trapped in floodwaters requiring boat rescue",
      "confidence": 0.94
    }"""
    mock_claude_response.content = [mock_block]

    with patch("backend.services.claude_service._get_anthropic_client") as mock_client_factory:
        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_claude_response
        mock_client_factory.return_value = mock_client

        payload = {"text": "कंकड़बाग पटना में भारी बाढ़, परिवार फंसे हुए हैं।"}
        res = client.post("/incidents", json=payload)
        assert res.status_code == 201
        data = res.json()
        assert data["original_language"] == "Hindi"
        assert data["location"] == "Kankarbagh, Patna"
        assert data["status"] == "new"
        # Base 3 + 'trapped' heuristic boost (+1) = 4
        assert data["severity"] == 4
        assert data["people_affected"] == 8


def test_claude_json_parse_error_returns_502():
    mock_claude_response = MagicMock()
    mock_block = MagicMock()
    mock_block.type = "text"
    mock_block.text = "This is not valid JSON at all."
    mock_claude_response.content = [mock_block]

    with patch("backend.services.claude_service._get_anthropic_client") as mock_client_factory:
        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_claude_response
        mock_client_factory.return_value = mock_client

        payload = {"text": "मदद करो"}
        res = client.post("/incidents", json=payload)
        assert res.status_code == 502
        assert "Invalid JSON from Claude" in res.json()["detail"]["error"]


if __name__ == "__main__":
    print("Running RapidRelay backend test suite...")
    test_severity_heuristics_no_keywords()
    test_severity_heuristics_boost_keywords()
    test_severity_heuristics_cap_at_five()
    test_api_health()
    test_get_incidents_list()
    test_get_incidents_filter()
    test_get_single_incident()
    test_status_forward_transition_and_reverse_rejection()
    test_post_incident_mock_claude()
    test_claude_json_parse_error_returns_502()
    print("ALL TESTS PASSED SUCCESSFULLY! (10/10)")
