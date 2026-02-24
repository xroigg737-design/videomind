"""Sketchnote visual format — Visual Thinking hand-drawn style.

Black marker strokes, large keywords, organic arrows, irregular boxes,
emoji icons, whiteboard/notebook feel, asymmetric layout.
Energy, dynamism, creative thinking.

Phase 3 transform: receives a structural model and produces a sketchnote JSON.
"""

from xml.sax.saxutils import escape as xml_escape

from pipeline.formats.base import VisualFormat, COLORS, html_page_sketch
from pipeline.formats.validators import check_list_length, check_word_count

TRANSFORM_SYSTEM = """\
You are a Visual Thinking Designer who creates bold, hand-drawn sketchnotes. \
You think in large keywords, vivid icons, and short action phrases. \
Your style is energetic, dynamic, and creative — like a whiteboard brainstorm. \
Every heading is 1-3 words UPPERCASE. Every point is 1-4 words maximum. \
You use active verbs and visual metaphors. You produce clean JSON."""

TRANSFORM_PROMPT = """\
Transform this structural model into a dynamic visual sketchnote.

STRUCTURAL MODEL:
{structural_model}

DESIGN PHILOSOPHY:
- Think like someone sketching on a whiteboard with a thick marker.
- Large keywords. Short punchy fragments. Visual energy.
- Not too symmetric — organic and alive.

STRICT RULES:
- Title: MAXIMUM 3 words, UPPERCASE, like a poster.
- 4 to 5 visual blocks (NEVER more than 5). Each block has:
  - id: "s1", "s2", etc.
  - heading: 1-3 words, UPPERCASE. Action-oriented.
  - icon: one expressive emoji (vivid, not generic — use ⚡🎯🧠🔥🚀💡🔗⚙️🎨📊)
  - points: 2-3 key fragments. MAXIMUM 4 words each. Active verbs.
  - color: from palette below
- 1-2 connections between blocks with single-verb labels (e.g. "fuels", "drives")
- Write like marker on whiteboard, NOT an essay.
- Every word must punch. No filler.

Colors: #4A90D9, #E67E22, #2ECC71, #9B59B6, #E74C3C, #1ABC9C, #F39C12, #3498DB

Return ONLY valid JSON:
{{
  "title": "BIG TITLE",
  "sections": [
    {{
      "id": "s1",
      "heading": "KEYWORD",
      "icon": "emoji",
      "points": ["action phrase", "concept"],
      "color": "#hex"
    }}
  ],
  "connections": [
    {{"from": "s1", "to": "s2", "label": "verb"}}
  ]
}}"""

# Legacy prompts kept for backward compatibility
SYSTEM_PROMPT = TRANSFORM_SYSTEM
EXTRACTION_PROMPT = """\
Turn this transcript into a visual sketchnote.
Title (max 3 words UPPERCASE), 4-5 blocks with heading (1-3 words),
icon, points (max 4 words each). 1-2 connections.
Return ONLY valid JSON.

TRANSCRIPT:
{transcript}"""


class SketchnoteFormat(VisualFormat):
    FORMAT_TYPE = "sketchnote"
    TRANSFORM_SYSTEM = TRANSFORM_SYSTEM
    TRANSFORM_PROMPT = TRANSFORM_PROMPT
    SYSTEM_PROMPT = SYSTEM_PROMPT
    EXTRACTION_PROMPT = EXTRACTION_PROMPT
    FILE_PREFIX = "mindmap"  # backward-compatible file naming

    # -- validation ----------------------------------------------------------

    def validate(self, data: dict) -> list:
        warnings = []
        sections = data.get("sections", [])
        w = check_list_length(sections, 4, 5, "sections")
        if w:
            warnings.append(w)
        w = check_word_count(data.get("title", ""), 3, "title")
        if w:
            warnings.append(w)
        for sec in sections:
            for pt in sec.get("points", []):
                w = check_word_count(pt, 4, f"point in '{sec.get('heading', '?')}'")
                if w:
                    warnings.append(w)
            w = check_word_count(sec.get("heading", ""), 3, f"heading '{sec.get('heading', '?')}'")
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

    # -- HTML / SVG (whiteboard sketchnote) ----------------------------------

    def generate_html(self, data: dict) -> str:
        title = xml_escape(data.get("title", "Sketchnote"))
        sections = data.get("sections", [])
        connections = data.get("connections", [])

        n = len(sections)
        positions = self._staggered_layout(n)
        svg_h = self._calc_height(positions)

        section_svgs = []
        for i, section in enumerate(sections):
            x, y, w, h = positions[i]
            section_svgs.append(self._svg_block(i, x, y, w, h, section))

        # Connection arrows
        conn_svgs = []
        for conn in connections:
            svg = self._svg_connection(conn, sections, positions)
            if svg:
                conn_svgs.append(svg)

        sections_markup = "\n    ".join(section_svgs)
        connections_markup = "\n    ".join(conn_svgs)

        svg_body = f"""
    <!-- Cream notebook background -->
    <rect width="1000" height="{svg_h}" fill="#FFFDF7" rx="4"/>

    <!-- Title — large, bold, hand-drawn -->
    <text x="500" y="65" font-family="'Caveat', cursive"
          font-size="48" font-weight="700" fill="#1a1a1a" text-anchor="middle"
          letter-spacing="2" filter="url(#sketchy)">{title}</text>
    <path d="M 200 80 Q 500 85 800 78" stroke="#333" stroke-width="3"
          fill="none" filter="url(#sketchy)" opacity="0.6"/>

    <!-- Connections (behind blocks) -->
    {connections_markup}

    <!-- Section blocks -->
    {sections_markup}"""

        return html_page_sketch(data.get("title", "Sketchnote"), svg_body, svg_h)

    # -- private helpers -----------------------------------------------------

    @staticmethod
    def _staggered_layout(n: int) -> list[tuple]:
        """Compute staggered asymmetric positions for blocks."""
        # Asymmetric 2-column layout with vertical stagger
        pad_x = 40
        start_y = 120
        box_w = 420
        box_h = 180
        gap_x = 60
        gap_y = 30

        positions = []
        for i in range(n):
            col = i % 2
            row = i // 2
            x = pad_x + col * (box_w + gap_x)
            y = start_y + row * (box_h + gap_y)
            # Stagger: odd columns shifted down
            if col == 1:
                y += 40
            # Slight horizontal variation
            x += (i * 17) % 15 - 7
            positions.append((x, y, box_w, box_h))

        return positions

    @staticmethod
    def _calc_height(positions: list[tuple]) -> int:
        """Calculate needed SVG height from positions."""
        if not positions:
            return 400
        max_bottom = max(y + h for _, y, _, h in positions)
        return max_bottom + 60

    def _svg_block(self, idx: int, x: int, y: int, w: int, h: int, section: dict) -> str:
        """Render a single sketchnote block with hand-drawn style."""
        color = xml_escape(section.get("color", COLORS[idx % len(COLORS)]))
        icon = xml_escape(section.get("icon", ""))
        heading = xml_escape(section.get("heading", ""))
        points = section.get("points", [])

        # Irregular rectangle path (hand-drawn look via sketchy filter)
        d = self._wonky_rect(x, y, w, h, idx)

        block = (
            f'<g>\n'
            # Shadow
            f'      <path d="{self._wonky_rect(x + 3, y + 3, w, h, idx)}" '
            f'fill="#E0DDD5" stroke="none" filter="url(#sketchy)"/>\n'
            # Main box — thick black stroke
            f'      <path d="{d}" fill="#FFFEF9" stroke="#222" stroke-width="3" '
            f'filter="url(#sketchy)"/>\n'
            # Colored accent bar at top
            f'      <rect x="{x + 8}" y="{y + 6}" width="{w - 16}" height="5" '
            f'rx="2" fill="{color}" opacity="0.7" filter="url(#sketchy)"/>\n'
        )

        # Icon + heading — BIG and bold
        block += (
            f'      <text x="{x + 20}" y="{y + 45}" '
            f'font-family="\'Caveat\', cursive" '
            f'font-size="32" font-weight="700" fill="#1a1a1a" '
            f'filter="url(#sketchy)">{icon}</text>\n'
            f'      <text x="{x + 55}" y="{y + 46}" '
            f'font-family="\'Caveat\', cursive" '
            f'font-size="28" font-weight="700" fill="{color}" '
            f'filter="url(#sketchy)">{heading}</text>\n'
        )

        # Points — marker style
        line_y = y + 80
        for pt in points[:3]:
            escaped = xml_escape(pt)
            block += (
                f'      <text x="{x + 28}" y="{line_y}" '
                f'font-family="\'Caveat\', cursive" '
                f'font-size="20" font-weight="400" fill="#333">'
                f'— {escaped}</text>\n'
            )
            line_y += 32

        block += "    </g>"
        return block

    @staticmethod
    def _wonky_rect(x: int, y: int, w: int, h: int, seed: int = 0) -> str:
        """Generate a slightly irregular rectangle SVG path."""
        s = seed + 1
        # Small corner offsets for hand-drawn feel
        d = 4
        tl = (x + (s * 3 % d), y + (s * 7 % d))
        tr = (x + w - (s * 11 % d), y + (s * 13 % d))
        br = (x + w - (s * 17 % d), y + h - (s * 19 % d))
        bl = (x + (s * 23 % d), y + h - (s * 29 % d))

        return (
            f"M {tl[0]} {tl[1]} "
            f"L {tr[0]} {tr[1]} "
            f"L {br[0]} {br[1]} "
            f"L {bl[0]} {bl[1]} Z"
        )

    @staticmethod
    def _svg_connection(conn: dict, sections: list, positions: list) -> str:
        """Generate a thick organic arrow between two blocks."""
        id_to_idx = {s["id"]: i for i, s in enumerate(sections)}
        from_idx = id_to_idx.get(conn.get("from", ""))
        to_idx = id_to_idx.get(conn.get("to", ""))
        if from_idx is None or to_idx is None:
            return ""

        fx, fy, fw, fh = positions[from_idx]
        tx, ty, tw, th = positions[to_idx]

        x1 = fx + fw // 2
        y1 = fy + fh // 2
        x2 = tx + tw // 2
        y2 = ty + th // 2

        # Organic curve with perpendicular offset
        cx = (x1 + x2) // 2 + (y2 - y1) // 3
        cy = (y1 + y2) // 2 - (x2 - x1) // 3

        label = xml_escape(conn.get("label", ""))
        label_x = (x1 + x2) // 2
        label_y = (y1 + y2) // 2 - 12

        parts = [
            f'<path d="M {x1} {y1} Q {cx} {cy} {x2} {y2}" '
            f'stroke="#333" stroke-width="3" fill="none" '
            f'marker-end="url(#arrowhead)" filter="url(#sketchy)" '
            f'opacity="0.7"/>',
        ]
        if label:
            parts.append(
                f'<text x="{label_x}" y="{label_y}" '
                f'font-family="\'Caveat\', cursive" '
                f'font-size="18" font-weight="700" fill="#555" '
                f'text-anchor="middle" filter="url(#sketchy)">'
                f'{label}</text>'
            )
        return "\n    ".join(parts)
