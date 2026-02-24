"""Layer 1 — Content Engine.

Extracts structured content from a transcript via LLM.
Returns STRICT JSON only — no HTML, no SVG, no coordinates.

The unified JSON structure is used by all visual formats
(infographic, mindmap, sketchnote).
"""

import json

import anthropic

from config import ANTHROPIC_API_KEY, CLAUDE_MODEL
from pipeline.formats.base import _extract_json_from_response, MAX_TRANSCRIPT_LENGTH


# ---------------------------------------------------------------------------
# System & user prompts
# ---------------------------------------------------------------------------

CONTENT_SYSTEM = """\
You are a content distillation engine. You extract the conceptual essence \
of any content into a strict, minimal JSON structure. \
You think in keywords and short fragments, NEVER sentences. \
You eliminate ruthlessly. You never produce HTML, SVG, or any markup. \
You classify content type accurately. You produce clean JSON only."""

CONTENT_PROMPT = """\
Analyze this transcript and extract its core ideas into a strict JSON structure.

RULES (MANDATORY — zero exceptions):
- Title: MAXIMUM 8 words. Clear, punchy.
- Central idea: MAXIMUM 20 words. The one-sentence thesis.
- Sections: MAXIMUM 4 sections. Each section has:
  - label: MAXIMUM 4 words. A concept name or action phrase.
  - bullets: MAXIMUM 3 bullets. Each bullet MAXIMUM 4 words.
  - example: MAXIMUM 10 words. One concrete example or application.
- Practice plan:
  - daily_5min: exactly 3 short phrases (MAXIMUM 5 words each)
  - weekly: exactly 1 short phrase (MAXIMUM 5 words)
- content_type: classify as one of:
  - "procedural" (step-by-step, how-to, method, process)
  - "conceptual" (theory, framework, model, abstract ideas)
  - "pedagogical" (teaching, inspiration, motivation, learning)
- cta_removed: any call-to-action or marketing phrase found and removed (or empty string)

ABSOLUTE CONSTRAINTS:
- No HTML. No SVG. No coordinates. No layout info.
- No long sentences. Keywords and fragments only.
- No marketing language. No "subscribe", "like", "follow".
- No filler words. Every word must carry meaning.
- Remove ALL redundancy. Merge similar ideas.
- If content has more than 4 main ideas, merge the least important ones.

EXAMPLES of GOOD labels/bullets:
- "Feedback loops" (2 words)
- "Test early, iterate" (3 words)
- "Automate repetition" (2 words)

EXAMPLES of BAD labels/bullets (TOO LONG):
- "The importance of getting feedback from users early" (TOO LONG)
- "How to automate repetitive tasks in your workflow" (TOO LONG)

Return ONLY valid JSON:
{{
  "title": "max 8 words",
  "central_idea": "max 20 words",
  "content_type": "procedural|conceptual|pedagogical",
  "sections": [
    {{
      "label": "max 4 words",
      "bullets": ["max 4 words", "max 4 words", "max 4 words"],
      "example": "max 10 words"
    }}
  ],
  "practice_plan": {{
    "daily_5min": ["short phrase", "short phrase", "short phrase"],
    "weekly": ["short phrase"]
  }},
  "cta_removed": "removed marketing text or empty string"
}}

TRANSCRIPT:
{transcript}"""


# ---------------------------------------------------------------------------
# Content extraction
# ---------------------------------------------------------------------------

def extract_content(transcript: str, language: str = "") -> dict:
    """Layer 1: Extract unified content JSON from transcript via LLM.

    Returns a dict with title, central_idea, content_type, sections,
    practice_plan, and cta_removed.
    """
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    if len(transcript) > MAX_TRANSCRIPT_LENGTH:
        transcript = transcript[:MAX_TRANSCRIPT_LENGTH] + "\n\n[...transcript truncated...]"

    prompt = CONTENT_PROMPT.format(transcript=transcript)
    if language and language != "unknown":
        prompt += (
            f"\n\nIMPORTANT: Write ALL content "
            f"(title, central_idea, labels, bullets, examples, practice_plan) "
            f"in {language}."
        )

    message = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=2048,
        system=CONTENT_SYSTEM,
        messages=[{"role": "user", "content": prompt}],
    )

    response_text = message.content[0].text.strip()
    return _extract_json_from_response(response_text)


def retry_content(
    previous_output: dict,
    violations: list[str],
    language: str = "",
) -> dict:
    """Ask LLM to fix violations in a previous content extraction."""
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    prev_json = json.dumps(previous_output, indent=2, ensure_ascii=False)
    violations_text = "\n".join(f"- {v}" for v in violations)

    prompt = (
        f"Your previous content extraction was:\n{prev_json}\n\n"
        f"It has these violations:\n{violations_text}\n\n"
        f"Fix ALL violations by shortening text and adjusting counts. "
        f"Return the corrected JSON only. Keep the same structure."
    )

    if language and language != "unknown":
        prompt += f"\n\nKeep ALL content in {language}."

    message = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=2048,
        system=CONTENT_SYSTEM,
        messages=[{"role": "user", "content": prompt}],
    )

    response_text = message.content[0].text.strip()
    return _extract_json_from_response(response_text)


# ---------------------------------------------------------------------------
# Content validation
# ---------------------------------------------------------------------------

def validate_content(data: dict) -> list[str]:
    """Validate the unified content JSON. Returns list of violations."""
    violations = []

    # Title
    title = data.get("title", "")
    if not title:
        violations.append("missing title")
    elif len(title.split()) > 8:
        violations.append(f"title has {len(title.split())} words (max 8)")

    # Central idea
    central = data.get("central_idea", "")
    if not central:
        violations.append("missing central_idea")
    elif len(central.split()) > 20:
        violations.append(f"central_idea has {len(central.split())} words (max 20)")

    # Content type
    ct = data.get("content_type", "")
    if ct not in ("procedural", "conceptual", "pedagogical"):
        violations.append(f"invalid content_type '{ct}'")

    # Sections
    sections = data.get("sections", [])
    if len(sections) > 4:
        violations.append(f"{len(sections)} sections (max 4)")
    if len(sections) < 1:
        violations.append("no sections found")

    for sec in sections:
        label = sec.get("label", "")
        if len(label.split()) > 4:
            violations.append(f"label '{label[:30]}' has {len(label.split())} words (max 4)")

        bullets = sec.get("bullets", [])
        if len(bullets) > 3:
            violations.append(f"section '{label[:20]}' has {len(bullets)} bullets (max 3)")

        for bullet in bullets:
            if len(bullet.split()) > 4:
                violations.append(f"bullet '{bullet[:30]}' has {len(bullet.split())} words (max 4)")

        example = sec.get("example", "")
        if example and len(example.split()) > 10:
            violations.append(f"example '{example[:30]}' has {len(example.split())} words (max 10)")

    # Practice plan
    plan = data.get("practice_plan", {})
    daily = plan.get("daily_5min", [])
    if len(daily) > 3:
        violations.append(f"daily_5min has {len(daily)} items (max 3)")
    for d in daily:
        if len(d.split()) > 5:
            violations.append(f"daily item '{d[:30]}' has {len(d.split())} words (max 5)")

    weekly = plan.get("weekly", [])
    if len(weekly) > 1:
        violations.append(f"weekly has {len(weekly)} items (max 1)")
    for w in weekly:
        if len(w.split()) > 5:
            violations.append(f"weekly item '{w[:30]}' has {len(w.split())} words (max 5)")

    return violations
