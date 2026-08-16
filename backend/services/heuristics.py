"""
Severity Heuristics Engine for RapidRelay.

WHY THIS EXISTS:
In life-critical disaster triage, LLM scoring alone can be unpredictable or conservative.
We augment AI extraction with deterministic, explainable keyword heuristics.

KEY DIFFERENTIATOR:
Scoring isn't a black box. First responders, incident commanders, and auditing agencies
need clear, auditable reasoning for why an incident is prioritized (e.g. vulnerable demographics
like pregnant women or children, or acute life-threats like drowning or structural collapse).
Every rule trigger is deterministic, transparent, and reproducible.
"""

import re
from typing import List, Tuple

# Core life-safety & high-vulnerability trigger keywords (case-insensitive)
# Covers acute danger indicators across original distress messages and translations
SEVERITY_KEYWORDS: List[str] = [
    "trapped",
    "unconscious",
    "child",
    "children",
    "elderly",
    "pregnant",
    "no water",
    "flood rising",
    "drowning",
    "collapsed",
    "bleeding",
]


def apply_severity_heuristics(
    original_text: str,
    translated_text: str,
    llm_severity: int
) -> int:
    """
    Applies rule-based heuristic boosts to the LLM-assigned severity score.

    Rules:
    - Case-insensitive search across both original_text and translated_text.
    - Each unique matched keyword adds +1 to the base severity score.
    - Resulting severity is strictly clamped to the maximum value of 5 (and minimum of 1).

    Args:
        original_text: The raw distress message in the source language.
        translated_text: English translation produced by Claude.
        llm_severity: Base severity (1-5) assessed by Claude.

    Returns:
        int: Boosted severity score capped at 5.
    """
    boosted_severity, _ = apply_severity_heuristics_with_details(
        original_text=original_text,
        translated_text=translated_text,
        llm_severity=llm_severity
    )
    return boosted_severity


def apply_severity_heuristics_with_details(
    original_text: str,
    translated_text: str,
    llm_severity: int
) -> Tuple[int, List[str]]:
    """
    Evaluates heuristic boost and returns both the boosted score and matched keywords for transparency.
    """
    combined_text = f"{original_text or ''} {translated_text or ''}".lower()
    matched_keywords: List[str] = []

    for keyword in SEVERITY_KEYWORDS:
        # Use regex word boundaries for precise matching (avoids false substrings like 'child' inside 'children')
        pattern = rf"\b{re.escape(keyword)}\b"
        if re.search(pattern, combined_text, flags=re.IGNORECASE):
            matched_keywords.append(keyword)
        elif keyword in combined_text and not keyword.isalpha():
            # For multi-word phrases or special scripts if word boundary is restrictive
            matched_keywords.append(keyword)

    # Base severity validation (ensure within 1-5 range)
    clamped_base = max(1, min(5, llm_severity))
    
    # Each matched distinct keyword adds +1
    boosted = clamped_base + len(matched_keywords)
    final_severity = max(1, min(5, boosted))

    return final_severity, matched_keywords
