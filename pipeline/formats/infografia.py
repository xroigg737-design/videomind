"""Infographic visual format — Clean vertical blocks.

Layout: Big title top → max 4 vertical blocks → generous whitespace.
Each block: label + bullets + example.
Max 40 visible words total.
No WHAT/WHY/IMPACT pattern. Clean, didactic, professional.

Uses unified content JSON from Layer 1 (Content Engine).
"""

from xml.sax.saxutils import escape as xml_escape

from pipeline.formats.base import (
    VisualFormat,
    DESIGN_TOKENS,
    SECTION_COLORS,
    html_page_clean,
    lighten_color,
)


class InfografiaFormat(VisualFormat):
    FORMAT_TYPE = "infografia"
    FILE_PREFIX = "infografia"

    # -- markdown ------------------------------------------------------------

    def generate_markdown(self, data: dict) -> str:
        lines = [f"# {data.get('title', 'Infografia')}\n"]
        central = data.get("central_idea", "")
        if central:
            lines.append(f"*{central}*\n")

        for sec in data.get("sections", []):
            label = sec.get("label", "")
            lines.append(f"## {label}\n")
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

    # -- HTML / SVG (clean vertical blocks) ----------------------------------

    def generate_html(self, data: dict, dalle_images: dict | None = None) -> str:
        title = xml_escape(data.get("title", "Infografia"))
        sections = data.get("sections", [])[:4]

        canvas_w = 800
        margin_x = 60
        content_w = canvas_w - 2 * margin_x
        spacing = DESIGN_TOKENS["spacing"]
        spacing_lg = DESIGN_TOKENS["spacing_lg"]
        radius = DESIGN_TOKENS["border_radius"]
        primary = DESIGN_TOKENS["primary"]
        accent = DESIGN_TOKENS["accent"]
        accent_light = DESIGN_TOKENS["accent_light"]

        # Resolve DALL-E images
        dalle_icon_uris = None
        dalle_bg_uri = None
        if dalle_images:
            icons_data = dalle_images.get("icons")
            if icons_data:
                dalle_icon_uris = icons_data.get("icon_uris")
            bg_data = dalle_images.get("background")
            if bg_data:
                dalle_bg_uri = bg_data.get("bg_uri")

        parts = []

        # White background
        parts.append(f'<rect width="{canvas_w}" height="2000" fill="{DESIGN_TOKENS["background"]}"/>')

        # DALL-E background texture (low opacity)
        if dalle_bg_uri:
            parts.append(
                f'<image href="{dalle_bg_uri}" x="0" y="0" '
                f'width="{canvas_w}" height="2000" '
                f'preserveAspectRatio="xMidYMid slice" opacity="0.06"/>'
            )

        # Big title — top, centered, bold
        y = 70
        parts.append(
            f'<text x="{canvas_w // 2}" y="{y}" '
            f'font-family="{DESIGN_TOKENS["font_heading"]}" '
            f'font-size="38" font-weight="700" fill="{accent}" '
            f'text-anchor="middle" letter-spacing="-0.5">{title}</text>'
        )

        # Subtle line under title
        y += 20
        parts.append(
            f'<line x1="{margin_x + 100}" y1="{y}" x2="{canvas_w - margin_x - 100}" y2="{y}" '
            f'stroke="{primary}" stroke-width="2" opacity="0.3"/>'
        )

        # Central idea — small, muted
        central = xml_escape(data.get("central_idea", ""))
        if central:
            y += 30
            parts.append(
                f'<text x="{canvas_w // 2}" y="{y}" '
                f'font-family="{DESIGN_TOKENS["font_body"]}" '
                f'font-size="14" font-weight="400" fill="{accent_light}" '
                f'text-anchor="middle">{central}</text>'
            )

        # Vertical blocks — one per section
        y += spacing_lg + 10
        n = len(sections)
        block_h = 140
        block_gap = spacing

        for i, sec in enumerate(sections):
            color = SECTION_COLORS[i % len(SECTION_COLORS)]
            color_bg = lighten_color(color, 0.92)
            label = xml_escape(sec.get("label", ""))
            bullets = sec.get("bullets", [])
            example = xml_escape(sec.get("example", ""))

            sy = y + i * (block_h + block_gap)

            # Block background with rounded corners
            parts.append(
                f'<rect x="{margin_x}" y="{sy}" width="{content_w}" '
                f'height="{block_h}" rx="{radius}" fill="{color_bg}"/>'
            )

            # Left color accent bar
            parts.append(
                f'<rect x="{margin_x}" y="{sy}" width="4" height="{block_h}" '
                f'rx="2" fill="{color}"/>'
            )

            # Section icon or number circle
            cx_num = margin_x + 30
            cy_num = sy + 30
            if dalle_icon_uris and i < len(dalle_icon_uris):
                parts.append(
                    f'<image href="{dalle_icon_uris[i]}" '
                    f'x="{cx_num - 16}" y="{cy_num - 16}" width="32" height="32" '
                    f'preserveAspectRatio="xMidYMid meet"/>'
                )
            else:
                parts.append(
                    f'<circle cx="{cx_num}" cy="{cy_num}" r="14" fill="{color}"/>'
                    f'<text x="{cx_num}" y="{cy_num + 1}" '
                    f'font-family="{DESIGN_TOKENS["font_heading"]}" '
                    f'font-size="14" font-weight="700" fill="white" '
                    f'text-anchor="middle" dominant-baseline="middle">{i + 1}</text>'
                )

            # Label — bold, colored
            parts.append(
                f'<text x="{margin_x + 56}" y="{sy + 35}" '
                f'font-family="{DESIGN_TOKENS["font_heading"]}" '
                f'font-size="18" font-weight="600" fill="{color}">{label}</text>'
            )

            # Bullets — clean, spaced
            bullet_y = sy + 65
            for b in bullets[:3]:
                escaped_b = xml_escape(b)
                parts.append(
                    f'<circle cx="{margin_x + 30}" cy="{bullet_y - 4}" r="3" fill="{color}" opacity="0.5"/>'
                    f'<text x="{margin_x + 42}" y="{bullet_y}" '
                    f'font-family="{DESIGN_TOKENS["font_body"]}" '
                    f'font-size="14" font-weight="400" fill="{accent}">{escaped_b}</text>'
                )
                bullet_y += 24

            # Example — italic, muted, at bottom of block
            if example:
                parts.append(
                    f'<text x="{margin_x + 28}" y="{sy + block_h - 14}" '
                    f'font-family="{DESIGN_TOKENS["font_body"]}" '
                    f'font-size="12" font-weight="400" fill="{accent_light}" '
                    f'font-style="italic">e.g. {example}</text>'
                )

        # Footer area
        footer_y = y + n * (block_h + block_gap) + spacing

        # Practice plan — micro footer
        plan = data.get("practice_plan", {})
        daily = plan.get("daily_5min", [])
        weekly = plan.get("weekly", [])

        if daily or weekly:
            parts.append(
                f'<line x1="{margin_x}" y1="{footer_y}" '
                f'x2="{canvas_w - margin_x}" y2="{footer_y}" '
                f'stroke="#E5E7EB" stroke-width="1"/>'
            )
            footer_y += 24
            parts.append(
                f'<text x="{margin_x}" y="{footer_y}" '
                f'font-family="{DESIGN_TOKENS["font_heading"]}" '
                f'font-size="12" font-weight="600" fill="{primary}" '
                f'letter-spacing="1">PRACTICE PLAN</text>'
            )
            footer_y += 20
            all_items = [f"Daily: {d}" for d in daily] + [f"Weekly: {w}" for w in weekly]
            item_text = xml_escape("  |  ".join(all_items))
            parts.append(
                f'<text x="{margin_x}" y="{footer_y}" '
                f'font-family="{DESIGN_TOKENS["font_body"]}" '
                f'font-size="11" font-weight="400" fill="{accent_light}">'
                f'{item_text}</text>'
            )
            footer_y += spacing

        # Calculate actual height
        canvas_h = footer_y + spacing
        # Fix the background rect height
        parts[0] = f'<rect width="{canvas_w}" height="{canvas_h}" fill="{DESIGN_TOKENS["background"]}"/>'

        svg_body = "\n    ".join(parts)
        return html_page_clean(data.get("title", "Infografia"), svg_body, canvas_w, canvas_h)
