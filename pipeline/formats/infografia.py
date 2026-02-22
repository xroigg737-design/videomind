"""Infografia visual format — 3-panel narrative layout.

Generates an infographic with Problem / Method / Result structure
in a vertical 16:9 layout.

Phase 3 transform: receives a structural model and produces an infografia JSON.
"""

from xml.sax.saxutils import escape as xml_escape

from pipeline.formats.base import VisualFormat, html_page_wrapper
from pipeline.formats.validators import (
    check_exact_count,
    check_word_count,
)

TRANSFORM_SYSTEM = """\
You are an expert infographic designer. You transform structured data into \
clear, visually compelling 3-panel infographics. You write punchy headlines, \
short bullet points, and memorable closing phrases. You are oriented toward \
communication and impact, not academic depth. \
You strictly respect word limits. You produce clean JSON."""

TRANSFORM_PROMPT = """\
Transform this structural model into a 3-panel infographic.

STRUCTURAL MODEL:
{structural_model}

STRICT RULES:
- Headline: maximum 8 words, attention-grabbing like a magazine cover.
- Exactly 3 sections:
  1. "Problema" — the challenge or question (mapped from problem/thesis/concept in the model)
  2. "Mètode" — the approach or method (mapped from method/argument/component)
  3. "Resultat" — the outcome or insight (mapped from result/conclusion/consequence)
- Each section has:
  - title: exactly "Problema", "Mètode", or "Resultat"
  - icon: one expressive emoji
  - bullets: 2-4 short bullets. MAXIMUM 10 words each.
- Closing phrase: maximum 12 words, memorable and quotable.
- Bullets should be crisp and scannable, not narrative.
- Oriented toward communication, not study.

Return ONLY valid JSON:
{{
  "type": "infografia",
  "headline": "Attention-grabbing headline (max 8 words)",
  "sections": [
    {{
      "title": "Problema",
      "icon": "emoji",
      "bullets": ["Short point (max 10 words)", "Short point"]
    }},
    {{
      "title": "Mètode",
      "icon": "emoji",
      "bullets": ["Short point (max 10 words)", "Short point"]
    }},
    {{
      "title": "Resultat",
      "icon": "emoji",
      "bullets": ["Short point (max 10 words)", "Short point"]
    }}
  ],
  "closing_phrase": "Memorable final takeaway (max 12 words)"
}}"""

# Legacy prompts kept for backward compatibility
SYSTEM_PROMPT = TRANSFORM_SYSTEM
EXTRACTION_PROMPT = """\
Turn this transcript into a 3-panel infographic.

Extract headline, 3 sections (Problema/Mètode/Resultat), closing phrase.
Return ONLY valid JSON.

TRANSCRIPT:
{transcript}"""

# Panel accent colors
PANEL_COLORS = {
    "Problema": "#E74C3C",
    "Mètode": "#3498DB",
    "Resultat": "#2ECC71",
}
EXPECTED_TITLES = {"Problema", "Mètode", "Resultat"}


class InfografiaFormat(VisualFormat):
    FORMAT_TYPE = "infografia"
    TRANSFORM_SYSTEM = TRANSFORM_SYSTEM
    TRANSFORM_PROMPT = TRANSFORM_PROMPT
    SYSTEM_PROMPT = SYSTEM_PROMPT
    EXTRACTION_PROMPT = EXTRACTION_PROMPT
    FILE_PREFIX = "infografia"

    # -- validation ----------------------------------------------------------

    def validate(self, data: dict) -> list:
        warnings = []

        sections = data.get("sections", [])
        w = check_exact_count(sections, 3, "sections")
        if w:
            warnings.append(w)

        w = check_word_count(data.get("headline", ""), 8, "headline")
        if w:
            warnings.append(w)

        w = check_word_count(data.get("closing_phrase", ""), 12, "closing_phrase")
        if w:
            warnings.append(w)

        titles = {s.get("title") for s in sections}
        if titles != EXPECTED_TITLES:
            warnings.append(f"Section titles should be {EXPECTED_TITLES}, got {titles}")

        for sec in sections:
            for bullet in sec.get("bullets", []):
                w = check_word_count(bullet, 10, f"bullet in '{sec.get('title', '?')}'")
                if w:
                    warnings.append(w)

        return warnings

    # -- markdown ------------------------------------------------------------

    def generate_markdown(self, data: dict) -> str:
        lines = [f"# {data.get('headline', 'Infografia')}\n"]

        for section in data.get("sections", []):
            icon = section.get("icon", "")
            title = section.get("title", "")
            lines.append(f"## {icon} {title}\n")
            for bullet in section.get("bullets", []):
                lines.append(f"- {bullet}")
            lines.append("")

        lines.append("---\n")
        closing = data.get("closing_phrase", "")
        if closing:
            lines.append(f"> *{closing}*\n")

        return "\n".join(lines) + "\n"

    # -- HTML / SVG (16:9 vertical panels) -----------------------------------

    def generate_html(self, data: dict) -> str:
        headline = xml_escape(data.get("headline", "Infografia"))
        sections = data.get("sections", [])
        closing = xml_escape(data.get("closing_phrase", ""))

        canvas_w, canvas_h = 1000, 563  # 16:9
        parts = []

        # Background
        parts.append(f'<rect width="{canvas_w}" height="{canvas_h}" fill="#FFFEF9" rx="8"/>')

        # Headline
        parts.append(
            f'<text x="{canvas_w // 2}" y="50" '
            f'font-family="\'Caveat\', \'Segoe Print\', cursive" '
            f'font-size="32" font-weight="bold" fill="#16213e" text-anchor="middle" '
            f'filter="url(#sketchy)">{headline}</text>'
        )
        parts.append(
            f'<line x1="200" y1="62" x2="800" y2="62" stroke="#e94560" stroke-width="2" '
            f'stroke-dasharray="8,4" opacity="0.5" filter="url(#sketchy)"/>'
        )

        # 3 panels
        panel_top = 80
        panel_h = 130
        panel_gap = 15
        panel_margin_x = 60

        for i, section in enumerate(sections):
            py = panel_top + i * (panel_h + panel_gap)
            title = section.get("title", "")
            icon = xml_escape(section.get("icon", ""))
            color = PANEL_COLORS.get(title, "#888")
            escaped_title = xml_escape(title)
            bullets = section.get("bullets", [])

            # Panel background
            parts.append(
                f'<rect x="{panel_margin_x}" y="{py}" width="{canvas_w - 2 * panel_margin_x}" '
                f'height="{panel_h}" rx="8" ry="8" fill="white" stroke="#ddd" stroke-width="1" '
                f'filter="url(#sketchy)"/>'
            )

            # Accent bar
            parts.append(
                f'<rect x="{panel_margin_x}" y="{py}" width="6" height="{panel_h}" '
                f'rx="3" fill="{color}"/>'
            )

            # Icon + Title
            parts.append(
                f'<text x="{panel_margin_x + 24}" y="{py + 28}" '
                f'font-family="\'Caveat\', \'Segoe Print\', cursive" '
                f'font-size="22" font-weight="bold" fill="{color}">'
                f'{icon} {escaped_title}</text>'
            )

            # Bullets
            bullet_y = py + 52
            for bullet in bullets[:4]:
                escaped_bullet = xml_escape(bullet)
                if len(escaped_bullet) > 70:
                    escaped_bullet = escaped_bullet[:67] + "..."
                parts.append(
                    f'<text x="{panel_margin_x + 28}" y="{bullet_y}" '
                    f'font-family="\'Caveat\', \'Segoe Print\', cursive" '
                    f'font-size="14" fill="#444">'
                    f'\u2022 {escaped_bullet}</text>'
                )
                bullet_y += 22

        # Closing phrase
        if closing:
            parts.append(
                f'<text x="{canvas_w // 2}" y="{canvas_h - 25}" '
                f'font-family="\'Caveat\', \'Segoe Print\', cursive" '
                f'font-size="18" fill="#555" text-anchor="middle" font-style="italic" '
                f'filter="url(#sketchy)">{closing}</text>'
            )

        svg_body = "\n    ".join(parts)
        return html_page_wrapper(data.get("headline", "Infografia"), svg_body, canvas_h)
