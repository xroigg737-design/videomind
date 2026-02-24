"""Pre-render quality validation.

Validates content before it reaches the layout engine.
If rules fail, triggers auto-reduction.

Quality rules:
- Max 40 visible words per visual
- No phrase longer than 4 words (bullets) or 8 words (title)
- Clear hierarchy (title > labels > bullets)
- Sufficient sections (at least 2)
"""

from pipeline.formats.content_reducer import (
    count_visible_words,
    force_reduce_to_word_limit,
    reduce_content,
)


def check_quality(data: dict) -> list[str]:
    """Run all quality checks. Returns list of issues (empty = pass)."""
    issues = []

    # Word count check
    total = count_visible_words(data)
    if total > 40:
        issues.append(f"total visible words: {total} (max 40)")

    # Long phrase check
    title = data.get("title", "")
    if len(title.split()) > 8:
        issues.append(f"title too long: {len(title.split())} words")

    for sec in data.get("sections", []):
        label = sec.get("label", "")
        if len(label.split()) > 4:
            issues.append(f"label '{label[:20]}' too long")

        for b in sec.get("bullets", []):
            if len(b.split()) > 4:
                issues.append(f"bullet '{b[:20]}' too long")

        example = sec.get("example", "")
        if example and len(example.split()) > 10:
            issues.append(f"example too long: {len(example.split())} words")

    # Hierarchy check
    sections = data.get("sections", [])
    if len(sections) < 2:
        issues.append(f"only {len(sections)} section(s), need at least 2")
    if len(sections) > 4:
        issues.append(f"{len(sections)} sections (max 4)")

    # Bullet check — each section should have at least 1 bullet
    for sec in sections:
        bullets = sec.get("bullets", [])
        if not bullets:
            issues.append(f"section '{sec.get('label', '?')[:20]}' has no bullets")

    return issues


def ensure_quality(data: dict) -> dict:
    """Validate and auto-fix content quality.

    Applies reduction pipeline if quality checks fail.
    Returns the cleaned data.
    """
    # First pass: standard reduction
    data = reduce_content(data)

    # Check quality
    issues = check_quality(data)
    if not issues:
        return data

    # Second pass: force word limit reduction
    data = force_reduce_to_word_limit(data, max_words=40)

    # Final check — log remaining issues but return best effort
    remaining = check_quality(data)
    if remaining:
        for issue in remaining:
            print(f"    Quality warning (post-reduction): {issue}")

    return data
