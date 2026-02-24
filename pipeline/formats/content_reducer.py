"""Layer 2 — Content Reduction Module.

Post-processes the unified content JSON to enforce strict brevity:
- Shortens long phrases automatically
- Removes redundant adjectives and filler words
- Converts sentences into keywords
- Enforces word limits strictly
- Removes ~30% verbosity when needed
"""

import re

# Words that add no visual value — removed aggressively
FILLER_WORDS = {
    # English
    "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "could",
    "should", "may", "might", "shall", "can", "very", "really", "quite",
    "just", "also", "even", "still", "already", "much", "many", "some",
    "any", "each", "every", "all", "both", "few", "more", "most", "other",
    "such", "than", "too", "so", "then", "there", "here", "that", "this",
    "these", "those", "its", "their", "our", "your", "his", "her",
    "about", "into", "through", "during", "before", "after", "above",
    "below", "between", "under", "again", "further", "once",
    # Spanish
    "el", "la", "los", "las", "un", "una", "unos", "unas", "es", "son",
    "fue", "ser", "estar", "tiene", "tienen", "hace", "muy", "también",
    "más", "menos", "este", "esta", "estos", "estas", "ese", "esa",
    "del", "al", "que", "como", "para", "por", "con", "sin",
    # Catalan
    "el", "la", "els", "les", "un", "una", "uns", "unes", "és", "són",
    "ser", "estar", "té", "tenen", "fa", "molt", "també", "més", "menys",
    "aquest", "aquesta", "aquests", "aquestes", "amb", "per", "sense",
}

# Redundant adjectives that don't add concrete meaning
REDUNDANT_ADJECTIVES = {
    # English
    "important", "significant", "essential", "crucial", "critical",
    "fundamental", "key", "major", "primary", "main", "basic",
    "simple", "complex", "different", "various", "specific",
    "particular", "general", "overall", "effective", "efficient",
    "successful", "powerful", "strong", "great", "good", "best",
    "new", "old", "current", "modern", "traditional", "innovative",
    # Spanish
    "importante", "significativo", "esencial", "crucial", "fundamental",
    "principal", "básico", "simple", "complejo", "diferente", "varios",
    "específico", "particular", "general", "efectivo", "eficiente",
    "exitoso", "poderoso", "fuerte", "bueno", "mejor", "nuevo",
    # Catalan
    "important", "significatiu", "essencial", "fonamental", "principal",
    "bàsic", "simple", "complex", "diferent", "diversos", "específic",
    "particular", "general", "efectiu", "eficient", "exitós",
}


def _strip_filler(text: str) -> str:
    """Remove filler words from a phrase, preserving meaning-carrying words."""
    words = text.split()
    filtered = [w for w in words if w.lower().strip(".,;:!?") not in FILLER_WORDS]
    # Always keep at least 1 word
    return " ".join(filtered) if filtered else text


def _strip_adjectives(text: str) -> str:
    """Remove redundant adjectives that don't add visual value."""
    words = text.split()
    filtered = [w for w in words if w.lower().strip(".,;:!?") not in REDUNDANT_ADJECTIVES]
    return " ".join(filtered) if filtered else text


def _truncate_to_words(text: str, max_words: int) -> str:
    """Hard-truncate text to max_words."""
    words = text.split()
    if len(words) <= max_words:
        return text
    return " ".join(words[:max_words])


def _sentence_to_keyword(text: str) -> str:
    """Convert a sentence-like string into a keyword phrase."""
    # Remove leading articles and connectors
    text = re.sub(r"^(how to |what is |why |the |a |an )", "", text, flags=re.IGNORECASE)
    text = re.sub(r"^(cómo |qué es |por qué |com |què és |per què )", "", text, flags=re.IGNORECASE)
    # Remove trailing punctuation
    text = text.rstrip(".,;:!?")
    return text.strip()


def reduce_phrase(text: str, max_words: int) -> str:
    """Apply full reduction pipeline to a single phrase."""
    if not text or len(text.split()) <= max_words:
        return text

    # Step 1: Convert sentence to keyword style
    text = _sentence_to_keyword(text)
    if len(text.split()) <= max_words:
        return text

    # Step 2: Remove filler words
    text = _strip_filler(text)
    if len(text.split()) <= max_words:
        return text

    # Step 3: Remove redundant adjectives
    text = _strip_adjectives(text)
    if len(text.split()) <= max_words:
        return text

    # Step 4: Hard truncate
    return _truncate_to_words(text, max_words)


def reduce_content(data: dict) -> dict:
    """Apply content reduction to the entire unified JSON structure.

    Enforces all word limits and removes ~30% verbosity.
    Returns a new dict (does not mutate the original).
    """
    result = {}

    # Title: max 8 words
    result["title"] = reduce_phrase(data.get("title", ""), 8)

    # Central idea: max 20 words
    result["central_idea"] = reduce_phrase(data.get("central_idea", ""), 20)

    # Content type: pass through
    result["content_type"] = data.get("content_type", "conceptual")

    # Sections: max 4, each with label (4 words), bullets (3x4 words), example (10 words)
    sections = data.get("sections", [])[:4]
    reduced_sections = []
    for sec in sections:
        reduced_sec = {
            "label": reduce_phrase(sec.get("label", ""), 4),
            "bullets": [
                reduce_phrase(b, 4) for b in sec.get("bullets", [])[:3]
            ],
            "example": reduce_phrase(sec.get("example", ""), 10),
        }
        # Remove empty bullets
        reduced_sec["bullets"] = [b for b in reduced_sec["bullets"] if b.strip()]
        reduced_sections.append(reduced_sec)

    result["sections"] = reduced_sections

    # Practice plan
    plan = data.get("practice_plan", {})
    result["practice_plan"] = {
        "daily_5min": [
            reduce_phrase(d, 5) for d in plan.get("daily_5min", [])[:3]
        ],
        "weekly": [
            reduce_phrase(w, 5) for w in plan.get("weekly", [])[:1]
        ],
    }

    # CTA removed: pass through
    result["cta_removed"] = data.get("cta_removed", "")

    return result


def count_visible_words(data: dict) -> int:
    """Count total visible words in the content (for the 40-word check)."""
    count = 0

    count += len(data.get("title", "").split())

    for sec in data.get("sections", []):
        count += len(sec.get("label", "").split())
        for b in sec.get("bullets", []):
            count += len(b.split())
        # Examples count too
        count += len(sec.get("example", "").split())

    return count


def force_reduce_to_word_limit(data: dict, max_words: int = 40) -> dict:
    """Aggressively reduce content until total visible words <= max_words.

    Strategy: progressively remove examples, then bullets, then shorten labels.
    Returns a new dict.
    """
    import copy
    result = copy.deepcopy(data)

    # Round 1: Remove all examples
    if count_visible_words(result) > max_words:
        for sec in result.get("sections", []):
            sec["example"] = ""

    # Round 2: Limit bullets to 2 per section
    if count_visible_words(result) > max_words:
        for sec in result.get("sections", []):
            sec["bullets"] = sec.get("bullets", [])[:2]

    # Round 3: Limit bullets to 1 per section
    if count_visible_words(result) > max_words:
        for sec in result.get("sections", []):
            sec["bullets"] = sec.get("bullets", [])[:1]

    # Round 4: Shorten all labels to 2 words
    if count_visible_words(result) > max_words:
        for sec in result.get("sections", []):
            sec["label"] = _truncate_to_words(sec.get("label", ""), 2)
            sec["bullets"] = [_truncate_to_words(b, 3) for b in sec.get("bullets", [])]

    # Round 5: Reduce sections to 3
    if count_visible_words(result) > max_words:
        result["sections"] = result.get("sections", [])[:3]

    return result
