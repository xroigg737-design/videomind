"""Sketchnote visual format — 4 visual quadrants with large icons.

Layout: Strong headline + 4 visual quadrants + large icon per section
        + minimal text + micro practice plan footer.
Hand-drawn aesthetic with Caveat font and subtle sketch filter.

Uses unified content JSON from Layer 1 (Content Engine).
"""

from xml.sax.saxutils import escape as xml_escape

from pipeline.formats.base import (
    VisualFormat,
    DESIGN_TOKENS,
    SECTION_COLORS,
    html_page_sketch,
    lighten_color,
)

# Large, expressive icons for each section position
SECTION_ICONS = ["💡", "🎯", "⚡", "🚀"]


class SketchnoteFormat(VisualFormat):
    FORMAT_TYPE = "sketchnote"
    FILE_PREFIX = "mindmap"  # backward-compatible file naming

    # -- markdown ------------------------------------------------------------

    def generate_markdown(self, data: dict) -> str:
        lines = [f"# {data.get('title', 'Sketchnote')}\n"]

        central = data.get("central_idea", "")
        if central:
            lines.append(f"*{central}*\n")

        for i, sec in enumerate(data.get("sections", [])):
            icon = SECTION_ICONS[i % len(SECTION_ICONS)]
            label = sec.get("label", "")
            lines.append(f"## {icon} {label}\n")
            for b in sec.get("bullets", []):
                lines.append(f"- {b}")
            example = sec.get("example", "")
            if example:
                lines.append(f"\n> {example}")
            lines.append("")

        plan = data.get("practice_plan", {})
        daily = plan.get("daily_5min", [])
        weekly = plan.get("weekly", [])
        if daily or weekly:
            lines.append("---\n")
            lines.append("**Practice Plan**\n")
            for d in daily:
                lines.append(f"- {d}")
            for w in weekly:
                lines.append(f"- Weekly: {w}")
            lines.append("")

        return "\n".join(lines) + "\n"

    # -- HTML / SVG (4 quadrants, hand-drawn style) --------------------------

    def generate_html(self, data: dict) -> str:
        title = xml_escape(data.get("title", "Sketchnote"))
        sections = data.get("sections", [])[:4]
        plan = data.get("practice_plan", {})

        canvas_w = 1000
        pad = 40
        quadrant_gap = 24
        title_area_h = 100
        footer_h = 80

        # 2x2 quadrant layout
        quad_w = (canvas_w - 2 * pad - quadrant_gap) // 2
        quad_h = 200

        n = len(sections)
        rows = (n + 1) // 2
        canvas_h = title_area_h + rows * (quad_h + quadrant_gap) + footer_h + pad

        accent = DESIGN_TOKENS["accent"]
        primary = DESIGN_TOKENS["primary"]
        font_sketch = DESIGN_TOKENS["font_sketch"]
        font_body = DESIGN_TOKENS["font_body"]
        radius = DESIGN_TOKENS["border_radius"]

        parts = []

        # Cream/warm background
        parts.append(f'<rect width="{canvas_w}" height="{canvas_h}" fill="#FAFAF8" rx="4"/>')

        # Strong headline — large, bold, centered, hand-drawn feel
        parts.append(
            f'<text x="{canvas_w // 2}" y="55" font-family="{font_sketch}" '
            f'font-size="44" font-weight="700" fill="{accent}" text-anchor="middle" '
            f'letter-spacing="1" filter="url(#sketchy)">{title}</text>'
        )

        # Underline swoosh
        parts.append(
            f'<path d="M {canvas_w // 2 - 150} 70 Q {canvas_w // 2} 76 {canvas_w // 2 + 150} 68" '
            f'stroke="{primary}" stroke-width="3" fill="none" '
            f'filter="url(#sketchy)" opacity="0.5"/>'
        )

        # Central idea — small subtitle
        central = xml_escape(data.get("central_idea", ""))
        if central:
            parts.append(
                f'<text x="{canvas_w // 2}" y="92" font-family="{font_body}" '
                f'font-size="13" font-weight="400" fill="#6B7280" '
                f'text-anchor="middle">{central}</text>'
            )

        # 4 quadrants — 2x2 grid
        for i, sec in enumerate(sections):
            col = i % 2
            row = i // 2

            qx = pad + col * (quad_w + quadrant_gap)
            qy = title_area_h + row * (quad_h + quadrant_gap)

            color = SECTION_COLORS[i % len(SECTION_COLORS)]
            color_bg = lighten_color(color, 0.94)
            icon = SECTION_ICONS[i % len(SECTION_ICONS)]
            label = xml_escape(sec.get("label", ""))
            bullets = sec.get("bullets", [])
            example = xml_escape(sec.get("example", ""))

            # Quadrant background — irregular hand-drawn rect
            d = self._wonky_rect(qx, qy, quad_w, quad_h, i)
            # Shadow
            parts.append(
                f'<path d="{self._wonky_rect(qx + 3, qy + 3, quad_w, quad_h, i)}" '
                f'fill="#E5E5E0" stroke="none" filter="url(#sketchy)"/>'
            )
            # Main box
            parts.append(
                f'<path d="{d}" fill="{color_bg}" stroke="{accent}" stroke-width="2" '
                f'filter="url(#sketchy)"/>'
            )
            # Top accent bar
            parts.append(
                f'<rect x="{qx + 10}" y="{qy + 6}" width="{quad_w - 20}" height="4" '
                f'rx="2" fill="{color}" opacity="0.6" filter="url(#sketchy)"/>'
            )

            # Large icon — prominent, left side
            parts.append(
                f'<text x="{qx + 28}" y="{qy + 52}" '
                f'font-size="36" filter="url(#sketchy)">{icon}</text>'
            )

            # Label — bold, hand-drawn, right of icon
            parts.append(
                f'<text x="{qx + 72}" y="{qy + 50}" font-family="{font_sketch}" '
                f'font-size="24" font-weight="700" fill="{color}" '
                f'filter="url(#sketchy)">{label}</text>'
            )

            # Bullets — clean, spaced
            bullet_y = qy + 85
            for b in bullets[:3]:
                escaped_b = xml_escape(b)
                parts.append(
                    f'<text x="{qx + 32}" y="{bullet_y}" font-family="{font_sketch}" '
                    f'font-size="18" font-weight="400" fill="#444" '
                    f'filter="url(#sketchy)">— {escaped_b}</text>'
                )
                bullet_y += 28

            # Example — subtle, at bottom
            if example:
                parts.append(
                    f'<text x="{qx + 28}" y="{qy + quad_h - 16}" font-family="{font_body}" '
                    f'font-size="11" font-weight="400" fill="#9CA3AF" '
                    f'font-style="italic">{example}</text>'
                )

        # Practice plan footer — micro, clean
        daily = plan.get("daily_5min", [])
        weekly = plan.get("weekly", [])
        footer_y = title_area_h + rows * (quad_h + quadrant_gap) + 10

        if daily or weekly:
            # Separator
            parts.append(
                f'<line x1="{pad + 50}" y1="{footer_y}" '
                f'x2="{canvas_w - pad - 50}" y2="{footer_y}" '
                f'stroke="#D1D5DB" stroke-width="1" stroke-dasharray="4,4"/>'
            )

            footer_y += 24
            parts.append(
                f'<text x="{canvas_w // 2}" y="{footer_y}" font-family="{font_sketch}" '
                f'font-size="18" font-weight="700" fill="{primary}" '
                f'text-anchor="middle" filter="url(#sketchy)">Practice Plan</text>'
            )

            footer_y += 22
            all_items = daily + [f"Weekly: {w}" for w in weekly]
            items_text = xml_escape("  ·  ".join(all_items))
            parts.append(
                f'<text x="{canvas_w // 2}" y="{footer_y}" font-family="{font_body}" '
                f'font-size="12" font-weight="400" fill="#6B7280" '
                f'text-anchor="middle">{items_text}</text>'
            )

        svg_body = "\n    ".join(parts)
        return html_page_sketch(data.get("title", "Sketchnote"), svg_body, canvas_h)

    # -- private helpers -----------------------------------------------------

    @staticmethod
    def _wonky_rect(x: int, y: int, w: int, h: int, seed: int = 0) -> str:
        """Generate a slightly irregular rectangle SVG path for hand-drawn feel."""
        s = seed + 1
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
