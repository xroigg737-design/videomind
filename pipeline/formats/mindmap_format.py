"""Mindmap visual format — Radial keyword map with curved connectors.

Layout: Central node + 3-4 branches + curved organic connectors.
Only keywords — no sentences, no rigid grid.
Clean, professional, with generous whitespace.

Uses unified content JSON from Layer 1 (Content Engine).
"""

import math

from xml.sax.saxutils import escape as xml_escape

from pipeline.formats.base import (
    VisualFormat,
    DESIGN_TOKENS,
    SECTION_COLORS,
    html_page_clean,
    lighten_color,
)


class MindmapFormat(VisualFormat):
    FORMAT_TYPE = "mindmap"
    FILE_PREFIX = "mindmap_tree"

    # -- markdown ------------------------------------------------------------

    def generate_markdown(self, data: dict) -> str:
        title = data.get("title", "Mind Map")
        lines = [f"# {title}\n"]

        central = data.get("central_idea", "")
        if central:
            lines.append(f"*{central}*\n")

        for sec in data.get("sections", []):
            label = sec.get("label", "")
            lines.append(f"## {label}\n")
            for b in sec.get("bullets", []):
                lines.append(f"  - {b}")
            example = sec.get("example", "")
            if example:
                lines.append(f"  > {example}")
            lines.append("")

        return "\n".join(lines) + "\n"

    # -- HTML / SVG (radial mindmap) -----------------------------------------

    def generate_html(self, data: dict) -> str:
        title = xml_escape(data.get("title", "Mind Map"))
        sections = data.get("sections", [])[:4]

        W, H = 1200, 800
        CX, CY = W // 2, H // 2

        primary = DESIGN_TOKENS["primary"]
        accent = DESIGN_TOKENS["accent"]
        bg = DESIGN_TOKENS["background"]
        radius = DESIGN_TOKENS["border_radius"]

        parts = []

        # Pure white background
        parts.append(f'<rect width="{W}" height="{H}" fill="{bg}"/>')

        # Subtle radial grid (very faint concentric circles)
        for r in [150, 300]:
            parts.append(
                f'<circle cx="{CX}" cy="{CY}" r="{r}" '
                f'fill="none" stroke="#F3F4F6" stroke-width="1"/>'
            )

        line_parts = []
        node_parts = []

        n = max(len(sections), 1)
        branch_radius = 260

        for i, sec in enumerate(sections):
            angle = (2 * math.pi * i / n) - math.pi / 2
            color = SECTION_COLORS[i % len(SECTION_COLORS)]
            color_light = lighten_color(color, 0.88)

            bx = CX + branch_radius * math.cos(angle)
            by = CY + branch_radius * math.sin(angle)

            # Curved bezier from center to branch
            perp_angle = angle + math.pi / 2
            ctrl_offset = 30 * (1 if i % 2 == 0 else -1)
            ctrl_r = branch_radius * 0.5
            ctrl_x = CX + ctrl_r * math.cos(angle) + ctrl_offset * math.cos(perp_angle)
            ctrl_y = CY + ctrl_r * math.sin(angle) + ctrl_offset * math.sin(perp_angle)

            line_parts.append(
                f'<path d="M {CX} {CY} Q {ctrl_x:.0f} {ctrl_y:.0f} {bx:.0f} {by:.0f}" '
                f'stroke="{color}" stroke-width="2.5" fill="none" opacity="0.5" '
                f'stroke-linecap="round"/>'
            )

            # Branch node — pill/rounded rect with label
            label = xml_escape(sec.get("label", ""))
            node_w = max(len(label) * 10, 100)
            node_h = 36
            node_parts.append(
                f'<rect x="{bx - node_w / 2:.0f}" y="{by - node_h / 2:.0f}" '
                f'width="{node_w}" height="{node_h}" rx="{radius}" '
                f'fill="{color_light}" stroke="{color}" stroke-width="1.5"/>\n'
                f'    <text x="{bx:.0f}" y="{by + 1:.0f}" '
                f'font-family="{DESIGN_TOKENS["font_heading"]}" '
                f'font-size="14" font-weight="600" fill="{color}" '
                f'text-anchor="middle" dominant-baseline="middle">{label}</text>'
            )

            # Bullet keywords as leaf nodes (small, organic positions)
            bullets = sec.get("bullets", [])
            leaf_radius = 90
            nc = len(bullets)
            if nc > 0:
                spread = math.pi / (n * 1.2)
                for j, bullet in enumerate(bullets):
                    offset = spread * (j - (nc - 1) / 2)
                    ca = angle + offset
                    lx = bx + leaf_radius * math.cos(ca)
                    ly = by + leaf_radius * math.sin(ca)

                    # Fine connection line
                    line_parts.append(
                        f'<line x1="{bx:.0f}" y1="{by:.0f}" '
                        f'x2="{lx:.0f}" y2="{ly:.0f}" '
                        f'stroke="{color}" stroke-width="1" opacity="0.3" '
                        f'stroke-linecap="round"/>'
                    )

                    escaped_b = xml_escape(bullet)
                    node_parts.append(
                        f'<circle cx="{lx:.0f}" cy="{ly:.0f}" r="3" '
                        f'fill="{color}" opacity="0.4"/>\n'
                        f'    <text x="{lx:.0f}" y="{ly + 16:.0f}" '
                        f'font-family="{DESIGN_TOKENS["font_body"]}" '
                        f'font-size="11" font-weight="400" fill="#6B7280" '
                        f'text-anchor="middle">{escaped_b}</text>'
                    )

        # Central node — large circle with title
        central_r = 60
        node_parts.append(
            f'<circle cx="{CX}" cy="{CY}" r="{central_r}" '
            f'fill="{primary}" stroke="none"/>\n'
            f'    <text x="{CX}" y="{CY + 1}" '
            f'font-family="{DESIGN_TOKENS["font_heading"]}" '
            f'font-size="16" font-weight="700" fill="white" '
            f'text-anchor="middle" dominant-baseline="middle" '
            f'letter-spacing="0.3">{title}</text>'
        )

        lines_svg = "\n    ".join(line_parts)
        nodes_svg = "\n    ".join(node_parts)

        svg_body = f"""
    {parts[0]}
    {parts[1]}
    {parts[2]}

    <!-- Curved connectors -->
    {lines_svg}

    <!-- Nodes -->
    {nodes_svg}"""

        return html_page_clean(data.get("title", "Mind Map"), svg_body, W, H)
