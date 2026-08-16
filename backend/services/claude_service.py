import os
import json
import re
from typing import Dict, Any, Optional
import anthropic
from fastapi import HTTPException, status
from dotenv import load_dotenv

load_dotenv()

# Hardcoded single model ID as required
MODEL_NAME = "claude-sonnet-4-5"

# EXACT verbatim system prompt as specified in requirements
TRIAGE_SYSTEM_PROMPT = """You are an emergency triage extraction system. Given a distress message in any language,
respond with ONLY valid JSON, no preamble, no markdown fences, matching this schema:

{
  "original_language": string,
  "translated_text": string,
  "location": string | null,
  "severity": integer (1-5, 5 = life-threatening/immediate),
  "need_type": "medical" | "rescue" | "food" | "water" | "shelter" | "other",
  "people_affected": integer | null,
  "summary": string (max 20 words, in English),
  "confidence": float (0-1)
}

If a field cannot be determined, use null. Never fabricate a location or headcount."""


def _get_anthropic_client() -> anthropic.Anthropic:
    """Initializes and returns the Anthropic client."""
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key or api_key.strip() == "" or api_key == "your_anthropic_api_key_here":
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={
                "error": "Anthropic API Key not configured",
                "message": "Please set a valid ANTHROPIC_API_KEY in backend/.env to run live triage extraction."
            }
        )
    return anthropic.Anthropic(api_key=api_key)


def _clean_json_text(raw_text: str) -> str:
    """Defensively removes markdown code blocks, backticks, and extraneous whitespace."""
    text = raw_text.strip()
    # Strip markdown code blocks like ```json ... ``` or ``` ... ```
    text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s*```$", "", text)
    return text.strip()


def extract_triage_data(distress_text: str) -> Dict[str, Any]:
    """
    Calls Claude to extract structured triage information from a raw distress message.
    
    Defensively parses JSON and maps unexpected formatting or API errors to an HTTP 502 Bad Gateway
    with structured details so the caller/frontend can handle it gracefully.
    """
    client = _get_anthropic_client()

    try:
        response = client.messages.create(
            model=MODEL_NAME,
            max_tokens=1000,
            system=TRIAGE_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": distress_text}]
        )
    except anthropic.APIConnectionError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={
                "error": "Claude API Connection Failure",
                "message": f"Could not connect to Anthropic API: {str(exc)}"
            }
        )
    except anthropic.RateLimitError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={
                "error": "Claude API Rate Limit Exceeded",
                "message": "Upstream rate limit reached. Please try again shortly or use demo mode."
            }
        )
    except anthropic.APIStatusError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={
                "error": "Claude API Error",
                "status_code": exc.status_code,
                "message": str(exc.message)
            }
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={
                "error": "Claude API Request Exception",
                "message": str(exc)
            }
        )

    # Extract response text content
    if not response.content:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={
                "error": "Empty AI Response",
                "message": "Claude returned an empty response with no content blocks."
            }
        )

    raw_response_text = ""
    for block in response.content:
        if getattr(block, "type", None) == "text" or hasattr(block, "text"):
            raw_response_text += block.text

    cleaned_text = _clean_json_text(raw_response_text)

    # Defensively attempt JSON parsing
    try:
        parsed_data = json.loads(cleaned_text)
    except json.JSONDecodeError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={
                "error": "Invalid JSON from Claude",
                "message": f"Failed to parse model output as JSON: {str(exc)}",
                "raw_output": raw_response_text[:500]
            }
        )

    if not isinstance(parsed_data, dict):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={
                "error": "Invalid Data Structure from Claude",
                "message": "Expected JSON object at root of response",
                "raw_output": raw_response_text[:500]
            }
        )

    # Validate essential schema fields
    required_fields = ["original_language", "translated_text", "severity", "need_type", "summary", "confidence"]
    missing_fields = [f for f in required_fields if f not in parsed_data]
    if missing_fields:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={
                "error": "Missing Required Schema Fields",
                "message": f"Claude output missed required fields: {', '.join(missing_fields)}",
                "parsed_data": parsed_data
            }
        )

    # Normalize need_type to lowercase
    if isinstance(parsed_data.get("need_type"), str):
        parsed_data["need_type"] = parsed_data["need_type"].strip().lower()

    # Ensure severity is an integer clamped 1-5
    try:
        parsed_data["severity"] = int(parsed_data["severity"])
        parsed_data["severity"] = max(1, min(5, parsed_data["severity"]))
    except (ValueError, TypeError):
        parsed_data["severity"] = 3  # safe fallback severity

    # Ensure confidence is float between 0 and 1
    try:
        parsed_data["confidence"] = float(parsed_data["confidence"])
        parsed_data["confidence"] = max(0.0, min(1.0, parsed_data["confidence"]))
    except (ValueError, TypeError):
        parsed_data["confidence"] = 0.5

    return parsed_data
