"""Phase 1 & 2 of the 4-phase pipeline: conceptual distillation and structural modeling.

Phase 1 — Deep conceptual distillation:
    Extract thesis, nuclear ideas, sub-ideas, content type, and memorable phrase
    from a raw transcript via Claude.

Phase 2 — Structural hierarchization:
    Reorganize the distilled content into a clean intermediate model based on
    the detected content type (narrative / academic / explanatory).
"""

import json

import anthropic

from config import ANTHROPIC_API_KEY, CLAUDE_MODEL
from pipeline.formats.base import _extract_json_from_response, MAX_TRANSCRIPT_LENGTH

# ---------------------------------------------------------------------------
# Phase 1 — Distillation prompt
# ---------------------------------------------------------------------------

DISTILLATION_SYSTEM = """\
You are a Visual Thinking Designer who distills complex content into ultra-concise \
conceptual structures. You think in single words and short fragments, never sentences. \
You prioritize visual impact and spatial clarity over information quantity. \
Every node must be 1-4 words maximum. You eliminate ruthlessly. \
Quality of synthesis > quantity of information. You produce clean JSON."""

DISTILLATION_PROMPT = """\
Analyze this transcript and extract its conceptual essence for visual representation.

VISUAL THINKING RULES (MANDATORY):
- Think like a designer, not a writer.
- Every single text node must be 1-4 words MAXIMUM. No exceptions.
- Prioritize VISUAL IMPACT over information completeness.
- Quality > Quantity. Less is more.
- Eliminate ALL redundancy. Merge similar ideas ruthlessly.
- Maximum 3 hierarchical levels total.

You MUST return:

1. "thesis": The core concept in MAXIMUM 4 words. One powerful phrase.
2. "content_type": Classify as one of:
   - "narrative" (problem → method → result)
   - "academic" (thesis → arguments → conclusions)
   - "explanatory" (concept → components → consequences)
3. "nuclear_ideas": Between 3 and 5 ideas (NEVER more than 5). Each with:
   - "idea": MAXIMUM 4 words. One concept fragment.
   - "sub_ideas": Exactly 2 sub-ideas, MAXIMUM 4 words each.
   - "structural_role": Based on content_type:
     * narrative → "problem", "method", or "result"
     * academic → "thesis", "argument", or "conclusion"
     * explanatory → "concept", "component", or "consequence"
4. "memorable_phrase": A punchy takeaway (max 6 words). Empty string if not applicable.

EXAMPLES of good 1-4 word nodes:
- "Disruptive innovation" (2 words)
- "Scale through automation" (3 words)
- "Data-driven decisions" (2 words)
- "Customer retention first" (3 words)

EXAMPLES of BAD nodes (too long):
- "The importance of using data to make better decisions" (TOO LONG)
- "How companies can scale their operations through automation" (TOO LONG)

Return ONLY valid JSON:
{{
  "thesis": "string (1-4 words)",
  "content_type": "narrative|academic|explanatory",
  "nuclear_ideas": [
    {{
      "idea": "string (1-4 words)",
      "sub_ideas": ["string (1-4 words)", "string (1-4 words)"],
      "structural_role": "string"
    }}
  ],
  "memorable_phrase": "string (max 6 words) or empty"
}}

TRANSCRIPT:
{transcript}"""


# ---------------------------------------------------------------------------
# Phase 1 — extract_core_structure
# ---------------------------------------------------------------------------

def extract_core_structure(transcript: str, language: str = "") -> dict:
    """Phase 1: Send transcript to Claude and extract the distilled core structure.

    Returns a dict with thesis, content_type, nuclear_ideas, memorable_phrase.
    """
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    if len(transcript) > MAX_TRANSCRIPT_LENGTH:
        transcript = transcript[:MAX_TRANSCRIPT_LENGTH] + "\n\n[...transcript truncated...]"

    prompt = DISTILLATION_PROMPT.format(transcript=transcript)
    if language and language != "unknown":
        prompt += (
            f"\n\nIMPORTANT: Write ALL content "
            f"(thesis, ideas, sub-ideas, memorable phrase) in {language}."
        )

    message = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=2048,
        system=DISTILLATION_SYSTEM,
        messages=[{"role": "user", "content": prompt}],
    )

    response_text = message.content[0].text.strip()
    return _extract_json_from_response(response_text)


# ---------------------------------------------------------------------------
# Phase 1 validation
# ---------------------------------------------------------------------------

def validate_distillation(core: dict) -> list[str]:
    """Validate Phase 1 output. Returns list of errors (empty = valid)."""
    errors = []

    thesis = core.get("thesis", "")
    if len(thesis.split()) > 4:
        errors.append(f"thesis has {len(thesis.split())} words (max 4)")

    ideas = core.get("nuclear_ideas", [])
    if len(ideas) > 5:
        errors.append(f"{len(ideas)} nuclear ideas (max 5)")
    if len(ideas) < 3:
        errors.append(f"{len(ideas)} nuclear ideas (min 3)")

    for ni in ideas:
        idea_words = len(ni.get("idea", "").split())
        if idea_words > 4:
            errors.append(f"idea '{ni['idea'][:30]}...' has {idea_words} words (max 4)")
        for si in ni.get("sub_ideas", []):
            si_words = len(si.split())
            if si_words > 4:
                errors.append(f"sub_idea '{si[:30]}...' has {si_words} words (max 4)")

    ct = core.get("content_type", "")
    if ct not in ("narrative", "academic", "explanatory"):
        errors.append(f"invalid content_type '{ct}'")

    phrase = core.get("memorable_phrase", "")
    if phrase and len(phrase.split()) > 6:
        errors.append(f"memorable_phrase has {len(phrase.split())} words (max 6)")

    return errors


# ---------------------------------------------------------------------------
# Phase 2 — build_structural_model
# ---------------------------------------------------------------------------

_ROLE_MAP = {
    "narrative": {"slots": ["problem", "method", "result"]},
    "academic": {"slots": ["thesis", "argument", "conclusion"]},
    "explanatory": {"slots": ["concept", "component", "consequence"]},
}


def build_structural_model(core: dict) -> dict:
    """Phase 2: Reorganize distilled content into a clean structural model.

    Groups nuclear ideas by their structural_role and produces a model
    suitable for Phase 3 format-specific transformation.
    """
    content_type = core.get("content_type", "explanatory")
    role_info = _ROLE_MAP.get(content_type, _ROLE_MAP["explanatory"])
    slots = role_info["slots"]

    # Group ideas by structural role
    grouped: dict[str, list] = {slot: [] for slot in slots}
    unassigned = []

    for ni in core.get("nuclear_ideas", []):
        role = ni.get("structural_role", "")
        if role in grouped:
            grouped[role].append(ni)
        else:
            unassigned.append(ni)

    # Distribute unassigned ideas to the emptiest slot
    for ni in unassigned:
        emptiest = min(slots, key=lambda s: len(grouped[s]))
        grouped[emptiest].append(ni)

    return {
        "thesis": core.get("thesis", ""),
        "content_type": content_type,
        "structure": grouped,
        "nuclear_ideas": core.get("nuclear_ideas", []),
        "memorable_phrase": core.get("memorable_phrase", ""),
    }
