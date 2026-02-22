"""Sketchnote visual format — migrated from pipeline/mindmap.py.

Generates a hand-drawn-style visual note with section boxes, icons, metaphors,
and connection arrows laid out in a responsive grid.
"""

from xml.sax.saxutils import escape as xml_escape

from pipeline.formats.base import VisualFormat, html_page_wrapper
from pipeline.formats.validators import check_list_length, check_word_count

SYSTEM_PROMPT = """You are a visual thinker and sketchnote artist. You transform content into \
vivid, hand-drawn-style visual notes. You think in images, metaphors, and short punchy phrases \
-- never in paragraphs. You prioritize visual impact and memorability over academic structure. \
You produce clean JSON output suitable for rendering as a sketchnote infographic."""

EXTRACTION_PROMPT = """\
Turn this transcript into a visual sketchnote. Think like an illustrator, not a professor.

Extract:
- A punchy title (max 5 words, like a poster headline)
- 4-8 visual blocks, each with:
  - A unique id (s1, s2, ...)
  - A short heading (2-4 words, fragment style)
  - An expressive emoji icon (pick vivid, unexpected ones)
  - A metaphor: one short visual metaphor for the block (e.g. "building bridges", "peeling the onion")
  - 2-4 key points as fragments (max 5-6 words each, no full sentences)
  - A hex color from the palette below
- 1-4 connections between related blocks with vivid labels (use verbs + imagery, e.g. "fuels", "unlocks", "feeds")

Style guide:
- Write like a whiteboard sketch, NOT an essay
- Use action words and imagery over abstract nouns
- Each point should feel like a sticky note, not a paragraph
- Icons should be playful and expressive, not generic

Use these colors for sections: #4A90D9, #E67E22, #2ECC71, #9B59B6, #E74C3C, #1ABC9C, #F39C12, #3498DB.

Return ONLY valid JSON matching this exact schema (no other text):
{{
  "title": "string - punchy topic",
  "sections": [
    {{
      "id": "s1",
      "heading": "short heading",
      "icon": "emoji",
      "metaphor": "visual metaphor phrase",
      "points": ["fragment point 1", "fragment point 2"],
      "color": "#hex"
    }}
  ],
  "connections": [
    {{ "from": "s1", "to": "s2", "label": "vivid relationship" }}
  ]
}}

TRANSCRIPT:
{transcript}"""


class SketchnoteFormat(VisualFormat):
    FORMAT_TYPE = "sketchnote"
    SYSTEM_PROMPT = SYSTEM_PROMPT
    EXTRACTION_PROMPT = EXTRACTION_PROMPT
    FILE_PREFIX = "mindmap"  # backward-compatible file naming

    # -- validation ----------------------------------------------------------

    def validate(self, data: dict) -> list:
        warnings = []
        sections = data.get("sections", [])
        w = check_list_length(sections, 4, 8, "sections")
        if w:
            warnings.append(w)
        for sec in sections:
            for pt in sec.get("points", []):
                w = check_word_count(pt, 6, f"point in '{sec.get('heading', '?')}'")
                if w:
                    warnings.append(w)
            w = check_word_count(sec.get("heading", ""), 4, f"heading '{sec.get('heading', '?')}'")
            if w:
                warnings.append(w)
        return warnings

    # -- markdown ------------------------------------------------------------

    def generate_markdown(self, data: dict) -> str:
        lines = [f"# {data['title']}\n"]

        for section in data.get("sections", []):
            icon = section.get("icon", "")
            heading = section.get("heading", "")
            lines.append(f"## {icon} {heading}\n")
            metaphor = section.get("metaphor", "")
            if metaphor:
                lines.append(f"> *{metaphor}*\n")
            for point in section.get("points", []):
                lines.append(f"- {point}")
            lines.append("")

        connections = data.get("connections", [])
        if connections:
            lines.append("## Connections\n")
            for conn in connections:
                lines.append(f"- {conn['from']} → {conn['to']}: {conn.get('label', '')}")
            lines.append("")

        return "\n".join(lines) + "\n"

    # -- HTML / SVG ----------------------------------------------------------

    def generate_html(self, data: dict) -> str:
        title = xml_escape(data.get("title", "Sketchnote"))
        sections = data.get("sections", [])
        connections = data.get("connections", [])

        positions, rows, cell_h = self._layout_sections(sections)
        svg_h = 100 + rows * cell_h + 40

        # Section boxes
        section_svgs = []
        for i, section in enumerate(sections):
            x, y, w, h = positions[i]
            color = xml_escape(section.get("color", "#4A90D9"))
            icon = xml_escape(section.get("icon", ""))
            heading = xml_escape(section.get("heading", ""))
            points = section.get("points", [])

            box = (
                f'<g transform="translate({x},{y})">\n'
                f'      <rect x="0" y="0" width="{w}" height="{h}" rx="12" ry="12" '
                f'fill="white" stroke="{color}" stroke-width="2.5" filter="url(#sketchy)"/>\n'
                f'      <text x="16" y="32" font-family="\'Caveat\', \'Segoe Print\', cursive" '
                f'font-size="22" font-weight="bold" fill="{color}">'
                f'{icon} {heading}</text>\n'
            )

            metaphor = section.get("metaphor", "")
            if metaphor:
                if len(metaphor) > 45:
                    metaphor = metaphor[:42] + "..."
                escaped_metaphor = xml_escape(metaphor)
                box += (
                    f'      <text x="16" y="52" font-family="\'Caveat\', \'Segoe Print\', cursive" '
                    f'font-size="13" fill="#888" font-style="italic">'
                    f'{escaped_metaphor}</text>\n'
                )

            line_y = 72 if metaphor else 58
            for point in points[:4]:
                escaped = xml_escape(point)
                if len(escaped) > 50:
                    escaped = escaped[:47] + "..."
                box += (
                    f'      <text x="20" y="{line_y}" '
                    f'font-family="\'Caveat\', \'Segoe Print\', cursive" '
                    f'font-size="15" fill="#444">'
                    f'\u2022 {escaped}</text>\n'
                )
                line_y += 24

            box += "    </g>"
            section_svgs.append(box)

        # Connection arrows
        conn_svgs = []
        for conn in connections:
            svg = self._svg_connection(conn, sections, positions)
            if svg:
                conn_svgs.append(svg)

        sections_markup = "\n    ".join(section_svgs)
        connections_markup = "\n    ".join(conn_svgs)

        svg_body = f"""
    <!-- Background -->
    <rect width="1000" height="{svg_h}" fill="#FFFEF9" rx="8"/>

    <!-- Title -->
    <text x="500" y="60" font-family="'Caveat', 'Segoe Print', cursive"
          font-size="36" font-weight="bold" fill="#16213e" text-anchor="middle"
          filter="url(#sketchy)">{title}</text>
    <line x1="250" y1="72" x2="750" y2="72" stroke="#e94560" stroke-width="2"
          stroke-dasharray="8,4" opacity="0.5" filter="url(#sketchy)"/>

    <!-- Connections (drawn behind boxes) -->
    {connections_markup}

    <!-- Section boxes -->
    {sections_markup}"""

        return html_page_wrapper(data.get("title", "Sketchnote"), svg_body, svg_h)

    # -- private helpers -----------------------------------------------------

    @staticmethod
    def _layout_sections(sections: list) -> tuple:
        """Compute grid positions for sections. Returns (positions, rows, cell_h)."""
        n = len(sections)
        cols = 2 if n <= 4 else 3
        rows = (n + cols - 1) // cols

        pad_x, pad_y = 40, 100
        cell_w = (1000 - 2 * pad_x) // cols
        cell_h = 220
        box_w = cell_w - 30
        box_h = cell_h - 20

        positions = []
        for i in range(n):
            col = i % cols
            row = i // cols
            x = pad_x + col * cell_w + 15
            y = pad_y + row * cell_h + 10
            positions.append((x, y, box_w, box_h))

        return positions, rows, cell_h

    @staticmethod
    def _svg_connection(conn: dict, sections: list, positions: list) -> str:
        """Generate an SVG path for a connection arrow between two sections."""
        id_to_idx = {s["id"]: i for i, s in enumerate(sections)}
        from_idx = id_to_idx.get(conn["from"])
        to_idx = id_to_idx.get(conn["to"])
        if from_idx is None or to_idx is None:
            return ""

        fx, fy, fw, fh = positions[from_idx]
        tx, ty, tw, th = positions[to_idx]

        x1 = fx + fw // 2
        y1 = fy + fh // 2
        x2 = tx + tw // 2
        y2 = ty + th // 2

        cx = (x1 + x2) // 2 + (y2 - y1) // 4
        cy = (y1 + y2) // 2 - (x2 - x1) // 4

        label = xml_escape(conn.get("label", ""))
        label_x = (x1 + x2) // 2
        label_y = (y1 + y2) // 2 - 8

        parts = [
            f'<path d="M {x1} {y1} Q {cx} {cy} {x2} {y2}" '
            f'stroke="#888" stroke-width="2" fill="none" '
            f'marker-end="url(#arrowhead)" filter="url(#sketchy)" '
            f'stroke-dasharray="6,3" opacity="0.6"/>',
        ]
        if label:
            parts.append(
                f'<text x="{label_x}" y="{label_y}" '
                f'font-family="\'Caveat\', \'Segoe Print\', cursive" '
                f'font-size="13" fill="#888" text-anchor="middle">'
                f'{label}</text>'
            )
        return "\n    ".join(parts)
