"""Mindmap visual format — radial hierarchical tree.

Generates a mind-map with a central node and radiating branches,
rendered as an SVG with curved connections.
"""

import math

from xml.sax.saxutils import escape as xml_escape

from pipeline.formats.base import VisualFormat, COLORS, html_page_wrapper
from pipeline.formats.validators import (
    check_list_length,
    check_max_depth,
    check_word_count,
)

SYSTEM_PROMPT = """You are an expert at distilling complex content into clear, hierarchical mind maps. \
You organize ideas into a central theme with branches and sub-branches. Your output is structured, \
direct, and uses infinitive verbs. You never use metaphors or decorative language — only clear, \
actionable concepts. You produce clean JSON suitable for rendering as a radial mind map."""

EXTRACTION_PROMPT = """\
Turn this transcript into a hierarchical mind map.

Extract:
- A central node (the main topic, max 6 words)
- 5-7 main branches, each with:
  - A title (max 6-8 words, use infinitive verbs, e.g. "Identify key patterns")
  - 0-4 children sub-ideas, each with:
    - A title (max 6-8 words)
    - Optionally further children (max depth: 3 levels total)

Style guide:
- Be direct and structured, like a textbook outline
- Use infinitive verbs (e.g. "Analyze", "Define", "Implement")
- No metaphors, no emojis, no decorative language
- Each node should be a clear, standalone concept

Return ONLY valid JSON matching this exact schema (no other text):
{{
  "type": "mindmap",
  "central_node": "Main Topic",
  "branches": [
    {{
      "title": "Branch title",
      "children": [
        {{
          "title": "Sub-idea",
          "children": []
        }}
      ]
    }}
  ]
}}

TRANSCRIPT:
{transcript}"""


class MindmapFormat(VisualFormat):
    FORMAT_TYPE = "mindmap"
    SYSTEM_PROMPT = SYSTEM_PROMPT
    EXTRACTION_PROMPT = EXTRACTION_PROMPT
    FILE_PREFIX = "mindmap_tree"

    # -- validation ----------------------------------------------------------

    def validate(self, data: dict) -> list:
        warnings = []
        branches = data.get("branches", [])
        w = check_list_length(branches, 5, 7, "branches")
        if w:
            warnings.append(w)

        w = check_word_count(data.get("central_node", ""), 6, "central_node")
        if w:
            warnings.append(w)

        def _check_nodes(node):
            w = check_word_count(node.get("title", ""), 8, f"node '{node.get('title', '?')}'")
            if w:
                warnings.append(w)
            w = check_max_depth(node, 3)
            if w:
                warnings.append(w)
            for child in node.get("children", []):
                _check_nodes(child)

        for branch in branches:
            _check_nodes(branch)

        return warnings

    # -- markdown ------------------------------------------------------------

    def generate_markdown(self, data: dict) -> str:
        lines = [f"# {data.get('central_node', 'Mind Map')}\n"]

        for branch in data.get("branches", []):
            lines.append(f"## {branch['title']}\n")
            self._md_children(branch.get("children", []), lines, depth=1)
            lines.append("")

        return "\n".join(lines) + "\n"

    @staticmethod
    def _md_children(children: list, lines: list, depth: int):
        indent = "  " * depth
        for child in children:
            lines.append(f"{indent}- {child['title']}")
            MindmapFormat._md_children(child.get("children", []), lines, depth + 1)

    # -- HTML / SVG (radial layout) ------------------------------------------

    def generate_html(self, data: dict) -> str:
        central = xml_escape(data.get("central_node", "Mind Map"))
        branches = data.get("branches", [])

        cx, cy = 500, 350
        svg_h = 700

        parts = []
        # Background
        parts.append(f'<rect width="1000" height="{svg_h}" fill="#FFFEF9" rx="8"/>')

        # Collect all elements (lines first, then nodes on top)
        line_parts = []
        node_parts = []

        n = len(branches)
        if n == 0:
            n = 1  # avoid division by zero

        for i, branch in enumerate(branches):
            angle = (2 * math.pi * i / n) - math.pi / 2  # start from top
            color = COLORS[i % len(COLORS)]
            branch_r = 220

            bx = cx + branch_r * math.cos(angle)
            by = cy + branch_r * math.sin(angle)

            # Curved line from center to branch
            ctrl_x = cx + (branch_r * 0.5) * math.cos(angle)
            ctrl_y = cy + (branch_r * 0.5) * math.sin(angle)
            line_parts.append(
                f'<path d="M {cx} {cy} Q {ctrl_x} {ctrl_y} {bx:.0f} {by:.0f}" '
                f'stroke="{color}" stroke-width="2.5" fill="none" filter="url(#sketchy)" opacity="0.7"/>'
            )

            # Branch node
            title = xml_escape(branch.get("title", ""))
            if len(title) > 30:
                title = title[:27] + "..."
            node_parts.append(self._svg_node(bx, by, title, color, is_branch=True))

            # Children
            children = branch.get("children", [])
            nc = len(children)
            if nc > 0:
                spread = min(math.pi / (n * 0.7), math.pi / 3)
                child_angles = [
                    angle + spread * (j - (nc - 1) / 2) / max(nc - 1, 1)
                    for j in range(nc)
                ]
                child_r = 120

                for j, child in enumerate(children):
                    ca = child_angles[j]
                    child_x = bx + child_r * math.cos(ca)
                    child_y = by + child_r * math.sin(ca)

                    # Line from branch to child
                    line_parts.append(
                        f'<line x1="{bx:.0f}" y1="{by:.0f}" x2="{child_x:.0f}" y2="{child_y:.0f}" '
                        f'stroke="{color}" stroke-width="1.5" opacity="0.5" filter="url(#sketchy)"/>'
                    )

                    child_title = xml_escape(child.get("title", ""))
                    if len(child_title) > 28:
                        child_title = child_title[:25] + "..."
                    node_parts.append(self._svg_node(child_x, child_y, child_title, color, is_branch=False))

                    # Grandchildren (depth 3)
                    for k, gc in enumerate(child.get("children", [])[:3]):
                        gc_angle = ca + (k - 1) * 0.25
                        gc_r = 80
                        gc_x = child_x + gc_r * math.cos(gc_angle)
                        gc_y = child_y + gc_r * math.sin(gc_angle)

                        line_parts.append(
                            f'<line x1="{child_x:.0f}" y1="{child_y:.0f}" x2="{gc_x:.0f}" y2="{gc_y:.0f}" '
                            f'stroke="{color}" stroke-width="1" opacity="0.35" stroke-dasharray="4,3" '
                            f'filter="url(#sketchy)"/>'
                        )

                        gc_title = xml_escape(gc.get("title", ""))
                        if len(gc_title) > 22:
                            gc_title = gc_title[:19] + "..."
                        node_parts.append(
                            f'<text x="{gc_x:.0f}" y="{gc_y:.0f}" '
                            f'font-family="\'Caveat\', \'Segoe Print\', cursive" '
                            f'font-size="12" fill="{color}" text-anchor="middle" '
                            f'dominant-baseline="middle" opacity="0.8">{gc_title}</text>'
                        )

        # Central node (drawn on top of everything)
        central_node = (
            f'<rect x="{cx - 90}" y="{cy - 28}" width="180" height="56" rx="28" ry="28" '
            f'fill="#16213e" stroke="#e94560" stroke-width="2.5" filter="url(#sketchy)"/>\n'
            f'    <text x="{cx}" y="{cy + 6}" font-family="\'Caveat\', \'Segoe Print\', cursive" '
            f'font-size="22" font-weight="bold" fill="#FFFEF9" text-anchor="middle" '
            f'dominant-baseline="middle">{central}</text>'
        )

        all_lines = "\n    ".join(line_parts)
        all_nodes = "\n    ".join(node_parts)

        svg_body = f"""
    {parts[0]}

    <!-- Connection lines -->
    {all_lines}

    <!-- Branch and leaf nodes -->
    {all_nodes}

    <!-- Central node -->
    {central_node}"""

        return html_page_wrapper(data.get("central_node", "Mind Map"), svg_body, svg_h)

    @staticmethod
    def _svg_node(x: float, y: float, text: str, color: str, is_branch: bool) -> str:
        """Render a single node (branch or leaf) as SVG."""
        if is_branch:
            w, h = 160, 40
            rx = 12
            return (
                f'<rect x="{x - w/2:.0f}" y="{y - h/2:.0f}" width="{w}" height="{h}" '
                f'rx="{rx}" ry="{rx}" fill="white" stroke="{color}" stroke-width="2" '
                f'filter="url(#sketchy)"/>\n'
                f'    <text x="{x:.0f}" y="{y + 5:.0f}" '
                f'font-family="\'Caveat\', \'Segoe Print\', cursive" '
                f'font-size="15" font-weight="bold" fill="{color}" text-anchor="middle" '
                f'dominant-baseline="middle">{text}</text>'
            )
        else:
            return (
                f'<text x="{x:.0f}" y="{y:.0f}" '
                f'font-family="\'Caveat\', \'Segoe Print\', cursive" '
                f'font-size="13" fill="#444" text-anchor="middle" '
                f'dominant-baseline="middle">{text}</text>'
            )
