"""Reusable validation functions for visual format data.

Supports both the new unified JSON schema (from Content Engine)
and legacy format-specific schemas for backward compatibility.
"""


def check_word_count(text: str, max_words: int, field_name: str) -> str | None:
    """Return a warning if *text* exceeds *max_words*, else None."""
    words = text.split()
    if len(words) > max_words:
        return f"{field_name}: {len(words)} words (max {max_words})"
    return None


def check_list_length(items: list, min_len: int, max_len: int, field_name: str) -> str | None:
    """Return a warning if list length is outside [min_len, max_len]."""
    n = len(items)
    if n < min_len or n > max_len:
        return f"{field_name}: {n} items (expected {min_len}-{max_len})"
    return None


def check_exact_count(items: list, exact: int, field_name: str) -> str | None:
    """Return a warning if list length != exact."""
    n = len(items)
    if n != exact:
        return f"{field_name}: {n} items (expected exactly {exact})"
    return None


def check_max_depth(node: dict, max_depth: int, _current: int = 1) -> str | None:
    """Return a warning if tree rooted at *node* exceeds *max_depth* levels."""
    if _current > max_depth:
        return f"Tree exceeds max depth {max_depth} at node '{node.get('title', '?')}'"
    for child in node.get("children", []):
        result = check_max_depth(child, max_depth, _current + 1)
        if result:
            return result
    return None


def collect_all_violations(data: dict, format_type: str) -> list[str]:
    """Run validation and return all violations as strings.

    Supports the unified JSON schema used by all formats.
    Returns an empty list if valid.
    """
    violations = []

    # Detect if this is the new unified schema
    if "sections" in data and "central_idea" in data:
        return _validate_unified(data)

    # Legacy format-specific validation (backward compat)
    if format_type == "mindmap":
        return _validate_legacy_mindmap(data)
    elif format_type == "sketchnote":
        return _validate_legacy_sketchnote(data)
    elif format_type == "infografia":
        return _validate_legacy_infografia(data)

    return violations


def _validate_unified(data: dict) -> list[str]:
    """Validate the unified content JSON schema."""
    violations = []

    # Title: max 8 words
    w = check_word_count(data.get("title", ""), 8, "title")
    if w:
        violations.append(w)

    # Central idea: max 20 words
    w = check_word_count(data.get("central_idea", ""), 20, "central_idea")
    if w:
        violations.append(w)

    # Sections: 1-4
    sections = data.get("sections", [])
    w = check_list_length(sections, 1, 4, "sections")
    if w:
        violations.append(w)

    for sec in sections:
        label = sec.get("label", "")
        w = check_word_count(label, 4, f"label '{label[:20]}'")
        if w:
            violations.append(w)

        bullets = sec.get("bullets", [])
        w = check_list_length(bullets, 0, 3, f"bullets of '{label[:20]}'")
        if w:
            violations.append(w)

        for b in bullets:
            w = check_word_count(b, 4, f"bullet in '{label[:20]}'")
            if w:
                violations.append(w)

        example = sec.get("example", "")
        if example:
            w = check_word_count(example, 10, f"example in '{label[:20]}'")
            if w:
                violations.append(w)

    # Practice plan
    plan = data.get("practice_plan", {})
    daily = plan.get("daily_5min", [])
    w = check_list_length(daily, 0, 3, "daily_5min")
    if w:
        violations.append(w)

    weekly = plan.get("weekly", [])
    w = check_list_length(weekly, 0, 1, "weekly")
    if w:
        violations.append(w)

    return violations


# ---------------------------------------------------------------------------
# Legacy validators (backward compat)
# ---------------------------------------------------------------------------

def _validate_legacy_mindmap(data: dict) -> list[str]:
    violations = []
    central = data.get("central_node", "")
    w = check_word_count(central, 4, "central_node")
    if w:
        violations.append(w)

    branches = data.get("branches", [])
    w = check_list_length(branches, 3, 5, "branches")
    if w:
        violations.append(w)

    for branch in branches:
        w = check_word_count(branch.get("title", ""), 4, f"branch '{branch.get('title', '?')}'")
        if w:
            violations.append(w)
        children = branch.get("children", [])
        w = check_list_length(children, 0, 2, f"children of '{branch.get('title', '?')}'")
        if w:
            violations.append(w)
        for child in children:
            w = check_word_count(child.get("title", ""), 4, f"child '{child.get('title', '?')}'")
            if w:
                violations.append(w)
    return violations


def _validate_legacy_sketchnote(data: dict) -> list[str]:
    violations = []
    w = check_word_count(data.get("title", ""), 3, "title")
    if w:
        violations.append(w)

    sections = data.get("sections", [])
    w = check_list_length(sections, 4, 5, "sections")
    if w:
        violations.append(w)
    for sec in sections:
        w = check_word_count(sec.get("heading", ""), 3, f"heading '{sec.get('heading', '?')}'")
        if w:
            violations.append(w)
        for pt in sec.get("points", []):
            w = check_word_count(pt, 4, f"point in '{sec.get('heading', '?')}'")
            if w:
                violations.append(w)
    return violations


def _validate_legacy_infografia(data: dict) -> list[str]:
    violations = []
    w = check_word_count(data.get("headline", ""), 4, "headline")
    if w:
        violations.append(w)

    sections = data.get("sections", [])
    w = check_list_length(sections, 3, 5, "sections")
    if w:
        violations.append(w)

    for sec in sections:
        w = check_word_count(sec.get("title", ""), 3, f"title '{sec.get('title', '?')}'")
        if w:
            violations.append(w)
        for field in ("what", "why", "impact"):
            val = sec.get(field, "")
            if val:
                w = check_word_count(val, 4, f"{field} in '{sec.get('title', '?')}'")
                if w:
                    violations.append(w)

    w = check_word_count(data.get("closing_phrase", ""), 6, "closing_phrase")
    if w:
        violations.append(w)
    return violations
