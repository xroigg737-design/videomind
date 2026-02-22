"""Reusable validation functions for visual format data."""


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
    """Run format-specific validation and return all violations as strings.

    Used by the Phase 4 auto-retry loop. Returns an empty list if valid.
    """
    violations = []

    if format_type == "mindmap":
        central = data.get("central_node", "")
        w = check_word_count(central, 6, "central_node")
        if w:
            violations.append(w)

        branches = data.get("branches", [])
        w = check_list_length(branches, 3, 5, "branches")
        if w:
            violations.append(w)

        for branch in branches:
            w = check_word_count(branch.get("title", ""), 8, f"branch '{branch.get('title', '?')}'")
            if w:
                violations.append(w)
            children = branch.get("children", [])
            w = check_list_length(children, 0, 2, f"children of '{branch.get('title', '?')}'")
            if w:
                violations.append(w)
            for child in children:
                w = check_word_count(child.get("title", ""), 8, f"child '{child.get('title', '?')}'")
                if w:
                    violations.append(w)

    elif format_type == "sketchnote":
        sections = data.get("sections", [])
        w = check_list_length(sections, 4, 6, "sections")
        if w:
            violations.append(w)
        for sec in sections:
            w = check_word_count(sec.get("heading", ""), 4, f"heading '{sec.get('heading', '?')}'")
            if w:
                violations.append(w)
            for pt in sec.get("points", []):
                w = check_word_count(pt, 6, f"point in '{sec.get('heading', '?')}'")
                if w:
                    violations.append(w)

    elif format_type == "infografia":
        w = check_word_count(data.get("headline", ""), 8, "headline")
        if w:
            violations.append(w)

        sections = data.get("sections", [])
        w = check_exact_count(sections, 3, "sections")
        if w:
            violations.append(w)

        for sec in sections:
            for bullet in sec.get("bullets", []):
                w = check_word_count(bullet, 10, f"bullet in '{sec.get('title', '?')}'")
                if w:
                    violations.append(w)

        w = check_word_count(data.get("closing_phrase", ""), 12, "closing_phrase")
        if w:
            violations.append(w)

    return violations
