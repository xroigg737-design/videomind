"""Infografia visual format — Executive Strategic Infographic.

BCG/McKinsey consulting aesthetic: vertical 4:5 layout, 3-5 sections,
each answering What/Why/Impact, clean sans-serif typography,
soft muted colors, lots of white space.

Phase 3 transform: receives a structural model and produces an infografia JSON.
"""

from xml.sax.saxutils import escape as xml_escape

from pipeline.formats.base import VisualFormat, INFOGRAFIA_COLORS, html_page_executive
from pipeline.formats.validators import (
    check_list_length,
    check_word_count,
)

TRANSFORM_SYSTEM = """\
You are a senior Visual Thinking Designer at a top consulting firm (McKinsey/BCG). \
You create executive infographics that are clean, professional, and impactful. \
Every word must earn its place. You think in strategic frameworks, not paragraphs. \
Short, crisp, scannable. You produce clean JSON."""

TRANSFORM_PROMPT = """\
Transform this structural model into an executive strategic infographic.

STRUCTURAL MODEL:
{structural_model}

DESIGN PHILOSOPHY:
- Think like a McKinsey consultant presenting to a C-suite.
- Professional, clean, solid. No decoration, no fluff.
- Each section answers: What? Why it matters? Impact?
- Maximum clarity with minimum words.

STRICT RULES:
- Headline: MAXIMUM 4 words. Executive-level, not academic.
- 3 to 5 sections (one per nuclear idea). NEVER more than 5.
- Each section has:
  - title: 1-3 words. The concept name.
  - icon: one clean emoji (professional: 📊 🎯 ⚡ 🔑 🏗️ 📈 🔍 💎 🛡️ ⚖️)
  - what: What is this? MAXIMUM 4 words.
  - why: Why does it matter? MAXIMUM 4 words.
  - impact: What's the impact? MAXIMUM 4 words.
- Closing phrase: MAXIMUM 6 words. Memorable executive takeaway.
- Use noun phrases and active fragments, not full sentences.
- No filler words. Every word must punch.

Return ONLY valid JSON:
{{
  "type": "infografia",
  "headline": "Executive Title (1-4 words)",
  "sections": [
    {{
      "title": "Concept (1-3 words)",
      "icon": "emoji",
      "what": "Definition (1-4 words)",
      "why": "Importance (1-4 words)",
      "impact": "Result (1-4 words)"
    }}
  ],
  "closing_phrase": "Takeaway (max 6 words)"
}}"""

# Legacy prompts kept for backward compatibility
SYSTEM_PROMPT = TRANSFORM_SYSTEM
EXTRACTION_PROMPT = """\
Turn this transcript into an executive infographic.
Headline (max 4 words), 3-5 sections with title/what/why/impact (max 4 words each),
closing phrase (max 6 words). Return ONLY valid JSON.

TRANSCRIPT:
{transcript}"""


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
        w = check_list_length(sections, 3, 5, "sections")
        if w:
            warnings.append(w)

        w = check_word_count(data.get("headline", ""), 4, "headline")
        if w:
            warnings.append(w)

        w = check_word_count(data.get("closing_phrase", ""), 6, "closing_phrase")
        if w:
            warnings.append(w)

        for sec in sections:
            w = check_word_count(sec.get("title", ""), 3, f"title '{sec.get('title', '?')}'")
            if w:
                warnings.append(w)
            for field in ("what", "why", "impact"):
                val = sec.get(field, "")
                if val:
                    w = check_word_count(val, 4, f"{field} in '{sec.get('title', '?')}'")
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
            what = section.get("what", "")
            why = section.get("why", "")
            impact = section.get("impact", "")
            if what:
                lines.append(f"- **What:** {what}")
            if why:
                lines.append(f"- **Why:** {why}")
            if impact:
                lines.append(f"- **Impact:** {impact}")
            lines.append("")

        lines.append("---\n")
        closing = data.get("closing_phrase", "")
        if closing:
            lines.append(f"> *{closing}*\n")

        return "\n".join(lines) + "\n"

    # -- HTML / SVG (executive vertical layout) ------------------------------

    def generate_html(self, data: dict) -> str:
        headline = xml_escape(data.get("headline", "Infografia"))
        sections = data.get("sections", [])
        closing = xml_escape(data.get("closing_phrase", ""))

        canvas_w, canvas_h = 800, 1000  # 4:5 aspect
        margin_x = 80
        content_w = canvas_w - 2 * margin_x

        parts = []

        # Pure white background
        parts.append(f'<rect width="{canvas_w}" height="{canvas_h}" fill="#FFFFFF"/>')

        # Headline — large, bold, dark
        parts.append(
            f'<text x="{canvas_w // 2}" y="90" '
            f'font-family="\'Inter\', -apple-system, sans-serif" '
            f'font-size="36" font-weight="700" fill="#1A1A2E" '
            f'text-anchor="middle" letter-spacing="-0.5">{headline}</text>'
        )

        # Subtle separator line
        parts.append(
            f'<line x1="{margin_x}" y1="110" x2="{canvas_w - margin_x}" y2="110" '
            f'stroke="#E0E0E0" stroke-width="1"/>'
        )

        # Sections
        n = len(sections)
        section_start_y = 145
        available_h = canvas_h - section_start_y - 100  # room for closing
        section_h = min(150, (available_h - (n - 1) * 20) // max(n, 1))
        section_gap = 20

        for i, section in enumerate(sections):
            sy = section_start_y + i * (section_h + section_gap)
            color = INFOGRAFIA_COLORS[i % len(INFOGRAFIA_COLORS)]
            color_light = self._lighten_color(color, 0.92)

            title = xml_escape(section.get("title", ""))
            icon = xml_escape(section.get("icon", ""))
            what = xml_escape(section.get("what", ""))
            why = xml_escape(section.get("why", ""))
            impact = xml_escape(section.get("impact", ""))

            # Section background — very subtle
            parts.append(
                f'<rect x="{margin_x}" y="{sy}" width="{content_w}" '
                f'height="{section_h}" rx="6" fill="{color_light}"/>'
            )

            # Left accent bar
            parts.append(
                f'<rect x="{margin_x}" y="{sy}" width="4" height="{section_h}" '
                f'rx="2" fill="{color}"/>'
            )

            # Icon
            parts.append(
                f'<text x="{margin_x + 24}" y="{sy + 32}" '
                f'font-size="24">{icon}</text>'
            )

            # Section title
            parts.append(
                f'<text x="{margin_x + 56}" y="{sy + 32}" '
                f'font-family="\'Inter\', -apple-system, sans-serif" '
                f'font-size="18" font-weight="600" fill="{color}">'
                f'{title}</text>'
            )

            # What / Why / Impact — three clean lines
            label_x = margin_x + 28
            value_x = margin_x + 100
            line_y = sy + 60

            for label, value in [("What", what), ("Why", why), ("Impact", impact)]:
                if value:
                    parts.append(
                        f'<text x="{label_x}" y="{line_y}" '
                        f'font-family="\'Inter\', -apple-system, sans-serif" '
                        f'font-size="11" font-weight="600" fill="#999" '
                        f'letter-spacing="0.5">{label.upper()}</text>'
                    )
                    parts.append(
                        f'<text x="{value_x}" y="{line_y}" '
                        f'font-family="\'Inter\', -apple-system, sans-serif" '
                        f'font-size="13" font-weight="400" fill="#444">'
                        f'{value}</text>'
                    )
                    line_y += 24

        # Closing phrase — subtle, centered
        if closing:
            parts.append(
                f'<line x1="{canvas_w // 2 - 60}" y1="{canvas_h - 70}" '
                f'x2="{canvas_w // 2 + 60}" y2="{canvas_h - 70}" '
                f'stroke="#E0E0E0" stroke-width="1"/>'
            )
            parts.append(
                f'<text x="{canvas_w // 2}" y="{canvas_h - 40}" '
                f'font-family="\'Inter\', -apple-system, sans-serif" '
                f'font-size="15" font-weight="500" fill="#888" '
                f'text-anchor="middle" font-style="italic" '
                f'letter-spacing="0.3">{closing}</text>'
            )

        svg_body = "\n    ".join(parts)
        return html_page_executive(data.get("headline", "Infografia"), svg_body, canvas_w, canvas_h)

    @staticmethod
    def _lighten_color(hex_color: str, factor: float) -> str:
        """Lighten a hex color toward white by the given factor (0-1)."""
        hex_color = hex_color.lstrip("#")
        r = int(hex_color[0:2], 16)
        g = int(hex_color[2:4], 16)
        b = int(hex_color[4:6], 16)
        r = int(r + (255 - r) * factor)
        g = int(g + (255 - g) * factor)
        b = int(b + (255 - b) * factor)
        return f"#{r:02x}{g:02x}{b:02x}"
