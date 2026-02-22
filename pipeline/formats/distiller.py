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
You are an expert at conceptual synthesis and information architecture. \
You distill complex, verbose content into its essential structure with surgical precision. \
You never use filler words. You think in concepts, not sentences. \
You produce clean JSON output."""

DISTILLATION_PROMPT = """\
Analyze this transcript and extract its deep conceptual structure.

You MUST return:

1. "thesis": The central thesis in a MAXIMUM of 15 words. Be precise and specific.
2. "content_type": Classify as one of:
   - "narrative" (has a problem, method, and result)
   - "academic" (has thesis, arguments, and conclusions)
   - "explanatory" (has a central concept, components, and consequences)
3. "nuclear_ideas": Between 3 and 5 ideas (NEVER more than 5). Each with:
   - "idea": Maximum 12 words. Convert narrative sentences into concepts.
   - "sub_ideas": Exactly 2 sub-ideas, maximum 8 words each.
   - "structural_role": Based on content_type:
     * narrative → "problem", "method", or "result"
     * academic → "thesis", "argument", or "conclusion"
     * explanatory → "concept", "component", or "consequence"
4. "memorable_phrase": A final memorable phrase (max 12 words). Empty string if not applicable.

STRICT RULES:
- Maximum 5 nuclear ideas. If you find more, merge the least important ones.
- Eliminate ALL redundancy. Two similar ideas must become one.
- Convert narrative/descriptive phrases into atomic concepts.
- Force synthesis: if an idea exceeds 12 words, rewrite it shorter.
- Sub-ideas must be 8 words or fewer. No exceptions.

Return ONLY valid JSON:
{{
  "thesis": "string (max 15 words)",
  "content_type": "narrative|academic|explanatory",
  "nuclear_ideas": [
    {{
      "idea": "string (max 12 words)",
      "sub_ideas": ["string (max 8 words)", "string (max 8 words)"],
      "structural_role": "string"
    }}
  ],
  "memorable_phrase": "string (max 12 words) or empty"
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
    if len(thesis.split()) > 15:
        errors.append(f"thesis has {len(thesis.split())} words (max 15)")

    ideas = core.get("nuclear_ideas", [])
    if len(ideas) > 5:
        errors.append(f"{len(ideas)} nuclear ideas (max 5)")
    if len(ideas) < 3:
        errors.append(f"{len(ideas)} nuclear ideas (min 3)")

    for ni in ideas:
        idea_words = len(ni.get("idea", "").split())
        if idea_words > 12:
            errors.append(f"idea '{ni['idea'][:30]}...' has {idea_words} words (max 12)")
        for si in ni.get("sub_ideas", []):
            si_words = len(si.split())
            if si_words > 8:
                errors.append(f"sub_idea '{si[:30]}...' has {si_words} words (max 8)")

    ct = core.get("content_type", "")
    if ct not in ("narrative", "academic", "explanatory"):
        errors.append(f"invalid content_type '{ct}'")

    phrase = core.get("memorable_phrase", "")
    if phrase and len(phrase.split()) > 12:
        errors.append(f"memorable_phrase has {len(phrase.split())} words (max 12)")

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
