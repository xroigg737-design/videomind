"""Mindmap visual format — Radial Executive Mindmap.

Minimalist Apple/consulting aesthetic: central dominant node,
4-5 symmetric branches with soft pastel colors, curved organic
connections, clean sans-serif typography, lots of white space.

Phase 3 transform: receives a structural model and produces a mindmap JSON.
"""

import math

from xml.sax.saxutils import escape as xml_escape

from pipeline.formats.base import VisualFormat, EXECUTIVE_COLORS, html_page_executive
from pipeline.formats.validators import (
    check_list_length,
    check_max_depth,
    check_word_count,
)

TRANSFORM_SYSTEM = """\
You are a senior Visual Thinking Designer specializing in executive radial mind maps. \
You create minimalist, Apple-style concept maps with surgical precision. \
Every node is 1-4 words maximum. You think in spatial hierarchy, not sentences. \
You prioritize white space, symmetry, and visual clarity. \
No decorative language. No emojis. No metaphors. Only crystal-clear concepts. \
You produce clean JSON."""

TRANSFORM_PROMPT = """\
Transform this structural model into a minimalist radial mind map.

STRUCTURAL MODEL:
{structural_model}

DESIGN PHILOSOPHY:
- Think like a designer at Apple or McKinsey, not a programmer.
- Clarity, order, and visual breathing space.
- Every word must earn its place.

STRICT RULES:
- Central node = the thesis. MAXIMUM 4 words. One powerful concept.
- 4 to 5 main branches (one per nuclear idea). NEVER more than 5.
- Each branch title: MAXIMUM 4 words. Concept fragments, not sentences.
- Each branch has EXACTLY 2 children (from sub_ideas). MAXIMUM 4 words each.
- Maximum depth: 2 levels (branches + children). No grandchildren.
- No emojis. No metaphors. No decorative language.
- Use infinitive verbs or noun phrases only.

Return ONLY valid JSON:
{{
  "type": "mindmap",
  "central_node": "Core Concept (1-4 words)",
  "branches": [
    {{
      "title": "Branch (1-4 words)",
      "children": [
        {{"title": "Detail (1-4 words)", "children": []}},
        {{"title": "Detail (1-4 words)", "children": []}}
      ]
    }}
  ]
}}"""

# Legacy prompts kept for backward compatibility
SYSTEM_PROMPT = TRANSFORM_SYSTEM
EXTRACTION_PROMPT = """\
Turn this transcript into a minimalist radial mind map.
Central node (max 4 words), 3-5 branches (max 4 words each),
2 children per branch (max 4 words each). No emojis, no metaphors.
Return ONLY valid JSON.

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

        w = check_word_count(data.get("central_node", ""), 4, "central_node")
        if w:
            warnings.append(w)

        for branch in branches:
            w = check_word_count(branch.get("title", ""), 4, f"branch '{branch.get('title', '?')}'")
            if w:
                warnings.append(w)
            children = branch.get("children", [])
            w = check_list_length(children, 0, 2, f"children of '{branch.get('title', '?')}'")
            if w:
                warnings.append(w)
            for child in children:
                w = check_word_count(child.get("title", ""), 4, f"child '{child.get('title', '?')}'")
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

    # -- HTML / SVG (executive radial layout) --------------------------------

    def generate_html(self, data: dict) -> str:
        central = xml_escape(data.get("central_node", "Mind Map"))
        branches = data.get("branches", [])

        W, H = 1200, 800
        CX, CY = W // 2, H // 2

        parts = []

        # Pure white background
        parts.append(f'<rect width="{W}" height="{H}" fill="#FFFFFF"/>')

        # Subtle dot grid for depth (very faint)
        for gx in range(0, W, 40):
            for gy in range(0, H, 40):
                parts.append(
                    f'<circle cx="{gx}" cy="{gy}" r="0.5" fill="#E8E8E8"/>'
                )

        line_parts = []
        node_parts = []

        n = max(len(branches), 1)
        branch_radius = 250

        for i, branch in enumerate(branches):
            angle = (2 * math.pi * i / n) - math.pi / 2
            color = EXECUTIVE_COLORS[i % len(EXECUTIVE_COLORS)]
            color_light = self._lighten_color(color, 0.85)

            bx = CX + branch_radius * math.cos(angle)
            by = CY + branch_radius * math.sin(angle)

            # Smooth bezier curve from center to branch
            # Control point offset perpendicular for organic feel
            perp_angle = angle + math.pi / 2
            ctrl_offset = 20 * (1 if i % 2 == 0 else -1)
            ctrl_r = branch_radius * 0.55
            ctrl_x = CX + ctrl_r * math.cos(angle) + ctrl_offset * math.cos(perp_angle)
            ctrl_y = CY + ctrl_r * math.sin(angle) + ctrl_offset * math.sin(perp_angle)

            line_parts.append(
                f'<path d="M {CX} {CY} Q {ctrl_x:.0f} {ctrl_y:.0f} {bx:.0f} {by:.0f}" '
                f'stroke="{color}" stroke-width="2.5" fill="none" opacity="0.6" '
                f'stroke-linecap="round"/>'
            )

            # Branch node — soft circle with text
            title = xml_escape(branch.get("title", ""))
            node_parts.append(self._svg_branch_node(bx, by, title, color, color_light))

            # Children — fine secondary branches
            children = branch.get("children", [])
            nc = len(children)
            if nc > 0:
                child_radius = 120
                spread = math.pi / (n * 1.0)
                for j, child in enumerate(children):
                    offset = spread * (j - (nc - 1) / 2) / max(nc - 1, 1)
                    ca = angle + offset
                    cx_child = bx + child_radius * math.cos(ca)
                    cy_child = by + child_radius * math.sin(ca)

                    # Fine connection line
                    line_parts.append(
                        f'<line x1="{bx:.0f}" y1="{by:.0f}" '
                        f'x2="{cx_child:.0f}" y2="{cy_child:.0f}" '
                        f'stroke="{color}" stroke-width="1" opacity="0.35" '
                        f'stroke-linecap="round"/>'
                    )

                    child_title = xml_escape(child.get("title", ""))
                    node_parts.append(
                        self._svg_leaf_node(cx_child, cy_child, child_title, color)
                    )

        # Central node — large, dominant circle
        central_r = 58
        node_parts.append(
            f'<circle cx="{CX}" cy="{CY}" r="{central_r}" '
            f'fill="#1A1A2E" stroke="none"/>\n'
            f'    <text x="{CX}" y="{CY + 2}" '
            f'font-family="\'Inter\', -apple-system, sans-serif" '
            f'font-size="17" font-weight="600" fill="#FFFFFF" '
            f'text-anchor="middle" dominant-baseline="middle" '
            f'letter-spacing="0.5">{central}</text>'
        )

        lines_svg = "\n    ".join(line_parts)
        nodes_svg = "\n    ".join(node_parts)

        svg_body = f"""
    {parts[0]}

    <!-- Connections -->
    {lines_svg}

    <!-- Nodes -->
    {nodes_svg}"""

        return html_page_executive(data.get("central_node", "Mind Map"), svg_body, W, H)

    @staticmethod
    def _svg_branch_node(x: float, y: float, text: str, color: str, color_light: str) -> str:
        """Render a branch node as a soft circle with text."""
        r = 42
        return (
            f'<circle cx="{x:.0f}" cy="{y:.0f}" r="{r}" '
            f'fill="{color_light}" stroke="{color}" stroke-width="1.5"/>\n'
            f'    <text x="{x:.0f}" y="{y + 1:.0f}" '
            f'font-family="\'Inter\', -apple-system, sans-serif" '
            f'font-size="13" font-weight="600" fill="{color}" '
            f'text-anchor="middle" dominant-baseline="middle">{text}</text>'
        )

    @staticmethod
    def _svg_leaf_node(x: float, y: float, text: str, color: str) -> str:
        """Render a leaf node as subtle text with a small dot."""
        return (
            f'<circle cx="{x:.0f}" cy="{y:.0f}" r="3" fill="{color}" opacity="0.4"/>\n'
            f'    <text x="{x:.0f}" y="{y + 16:.0f}" '
            f'font-family="\'Inter\', -apple-system, sans-serif" '
            f'font-size="11" font-weight="400" fill="#666" '
            f'text-anchor="middle" dominant-baseline="middle">{text}</text>'
        )

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
