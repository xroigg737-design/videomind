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
