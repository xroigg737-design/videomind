"""Mindmap visual format — radial hierarchical tree.

Generates a mind-map with a central node and radiating branches,
rendered as an SVG with curved connections.

Phase 3 transform: receives a structural model and produces a mindmap JSON.
"""

import math

from xml.sax.saxutils import escape as xml_escape

from pipeline.formats.base import VisualFormat, COLORS, html_page_wrapper
from pipeline.formats.validators import (
    check_list_length,
    check_max_depth,
    check_word_count,
)

TRANSFORM_SYSTEM = """\
You are an expert at creating clear, hierarchical mind maps from structured data. \
You organize ideas into a central theme with branches and sub-branches. \
You are direct, precise, and use infinitive verbs. \
You NEVER use metaphors, emojis, or decorative language — only clear, actionable concepts. \
You strictly respect word limits. You produce clean JSON."""

TRANSFORM_PROMPT = """\
Transform this structural model into a hierarchical mind map.

STRUCTURAL MODEL:
{structural_model}

STRICT RULES:
- Central node = the thesis. Maximum 6 words.
- 3 to 5 main branches (one per nuclear idea). NEVER more than 5.
- Each branch title: maximum 8 words. Use infinitive verbs.
- Each branch has EXACTLY 2 children (from the sub_ideas). Maximum 8 words each.
- Maximum depth: 2 levels (branches + children). No grandchildren.
- No metaphors. No emojis. No decorative language.
- No long phrases. If a concept exceeds the word limit, rewrite it shorter.

Return ONLY valid JSON:
{{
  "type": "mindmap",
  "central_node": "Thesis (max 6 words)",
  "branches": [
    {{
      "title": "Branch title (max 8 words)",
      "children": [
        {{"title": "Sub-idea (max 8 words)", "children": []}},
        {{"title": "Sub-idea (max 8 words)", "children": []}}
      ]
    }}
  ]
}}"""

# Legacy prompts kept for backward compatibility
SYSTEM_PROMPT = TRANSFORM_SYSTEM
EXTRACTION_PROMPT = """\
Turn this transcript into a hierarchical mind map.

Extract:
- A central node (the main topic, max 6 words)
- 3-5 main branches, each with:
  - A title (max 8 words, use infinitive verbs)
  - 2 children sub-ideas, each with:
    - A title (max 8 words)

Style guide:
- Be direct and structured, like a textbook outline
- Use infinitive verbs
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
        {{"title": "Sub-idea", "children": []}},
        {{"title": "Sub-idea", "children": []}}
      ]
    }}
  ]
}}

TRANSCRIPT:
{transcript}"""


class MindmapFormat(VisualFormat):
    FORMAT_TYPE = "mindmap"
    TRANSFORM_SYSTEM = TRANSFORM_SYSTEM
    TRANSFORM_PROMPT = TRANSFORM_PROMPT
    SYSTEM_PROMPT = SYSTEM_PROMPT
    EXTRACTION_PROMPT = EXTRACTION_PROMPT
    FILE_PREFIX = "mindmap_tree"

    # -- validation ----------------------------------------------------------

    def validate(self, data: dict) -> list:
        warnings = []
        branches = data.get("branches", [])
        w = check_list_length(branches, 3, 5, "branches")
        if w:
            warnings.append(w)

        w = check_word_count(data.get("central_node", ""), 6, "central_node")
        if w:
            warnings.append(w)

        for branch in branches:
            w = check_word_count(branch.get("title", ""), 8, f"branch '{branch.get('title', '?')}'")
            if w:
                warnings.append(w)
            children = branch.get("children", [])
            w = check_list_length(children, 0, 2, f"children of '{branch.get('title', '?')}'")
            if w:
                warnings.append(w)
            for child in children:
                w = check_word_count(child.get("title", ""), 8, f"child '{child.get('title', '?')}'")
                if w:
                    warnings.append(w)
                w = check_max_depth(child, 2)
                if w:
                    warnings.append(w)

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
