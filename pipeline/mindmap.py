"""Sketchnote generation using Claude API.

Analyzes a transcript and produces structured sketchnote output
in Markdown, HTML (SVG), and JSON formats.
"""

import json
import os
from xml.sax.saxutils import escape as xml_escape

import anthropic

from config import ANTHROPIC_API_KEY, CLAUDE_MODEL

# Maximum transcript characters to send to Claude (to stay within context limits)
MAX_TRANSCRIPT_LENGTH = 100_000

SYSTEM_PROMPT = """You are an expert at analyzing educational and informational content \
and creating structured visual sketchnotes. You extract key ideas, organize them \
into thematic sections, and identify relationships between concepts. \
You produce clean JSON output suitable for rendering as a hand-drawn style infographic."""

EXTRACTION_PROMPT = """\
Analyze the following transcript and create a structured sketchnote.

Extract:
- A short title summarizing the content
- 4-8 thematic sections, each with:
  - A unique id (s1, s2, ...)
  - A short heading (2-4 words)
  - An emoji icon representing the section
  - 2-4 concise key points (bullet-length)
  - A hex color from the palette below
- 1-4 connections between related sections

Use these colors for sections: #4A90D9, #E67E22, #2ECC71, #9B59B6, #E74C3C, #1ABC9C, #F39C12, #3498DB.

Return ONLY valid JSON matching this exact schema (no other text):
{{
  "title": "string - main topic",
  "sections": [
    {{
      "id": "s1",
      "heading": "short heading",
      "icon": "emoji",
      "points": ["key point 1", "key point 2"],
      "color": "#hex"
    }}
  ],
  "connections": [
    {{ "from": "s1", "to": "s2", "label": "relationship" }}
  ]
}}

TRANSCRIPT:
{transcript}"""


def _call_claude(transcript: str, language: str = "") -> dict:
    """Send transcript to Claude and parse the JSON response."""
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    # Truncate very long transcripts
    if len(transcript) > MAX_TRANSCRIPT_LENGTH:
        transcript = transcript[:MAX_TRANSCRIPT_LENGTH] + "\n\n[...transcript truncated...]"

    prompt = EXTRACTION_PROMPT.format(transcript=transcript)
    if language and language != "unknown":
        prompt += (
            f"\n\nIMPORTANT: Write ALL content "
            f"(title, headings, points, connection labels) in {language}."
        )

    message = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=4096,
        system=SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": prompt,
            }
        ],
    )

    response_text = message.content[0].text.strip()

    # Extract JSON from response (handle possible markdown code blocks)
    if response_text.startswith("```"):
        lines = response_text.split("\n")
        json_lines = []
        inside = False
        for line in lines:
            if line.strip().startswith("```") and not inside:
                inside = True
                continue
            if line.strip() == "```" and inside:
                break
            if inside:
                json_lines.append(line)
        response_text = "\n".join(json_lines)

    return json.loads(response_text)


def _generate_markdown(data: dict) -> str:
    """Generate a Markdown sketchnote summary."""
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


def _layout_sections(sections: list) -> list:
    """Compute grid positions for sections. Returns list of (x, y, w, h) tuples."""
    n = len(sections)
    cols = 2 if n <= 4 else 3
    rows = (n + cols - 1) // cols

    pad_x, pad_y = 40, 100  # padding from edges; top padding for title
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


def _svg_connection(conn: dict, sections: list, positions: list) -> str:
    """Generate an SVG path for a connection arrow between two sections."""
    id_to_idx = {s["id"]: i for i, s in enumerate(sections)}
    from_idx = id_to_idx.get(conn["from"])
    to_idx = id_to_idx.get(conn["to"])
    if from_idx is None or to_idx is None:
        return ""

    fx, fy, fw, fh = positions[from_idx]
    tx, ty, tw, th = positions[to_idx]

    # Center points
    x1 = fx + fw // 2
    y1 = fy + fh // 2
    x2 = tx + tw // 2
    y2 = ty + th // 2

    # Control point for curve
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


def _generate_html(data: dict) -> str:
    """Generate a self-contained HTML page with an SVG sketchnote."""
    title = xml_escape(data.get("title", "Sketchnote"))
    sections = data.get("sections", [])
    connections = data.get("connections", [])

    positions, rows, cell_h = _layout_sections(sections)
    svg_h = 100 + rows * cell_h + 40  # title area + grid + bottom padding

    # Build section boxes
    section_svgs = []
    for i, section in enumerate(sections):
        x, y, w, h = positions[i]
        color = xml_escape(section.get("color", "#4A90D9"))
        icon = xml_escape(section.get("icon", ""))
        heading = xml_escape(section.get("heading", ""))
        points = section.get("points", [])

        # Box with sketchy filter
        box = (
            f'<g transform="translate({x},{y})">\n'
            f'      <rect x="0" y="0" width="{w}" height="{h}" rx="12" ry="12" '
            f'fill="white" stroke="{color}" stroke-width="2.5" filter="url(#sketchy)"/>\n'
            f'      <text x="16" y="32" font-family="\'Caveat\', \'Segoe Print\', cursive" '
            f'font-size="22" font-weight="bold" fill="{color}">'
            f'{icon} {heading}</text>\n'
        )

        # Bullet points
        line_y = 58
        for point in points[:4]:
            escaped = xml_escape(point)
            # Truncate long points to fit in box
            if len(escaped) > 50:
                escaped = escaped[:47] + "..."
            box += (
                f'      <text x="20" y="{line_y}" '
                f'font-family="\'Caveat\', \'Segoe Print\', cursive" '
                f'font-size="15" fill="#444">'
                f'• {escaped}</text>\n'
            )
            line_y += 24

        box += "    </g>"
        section_svgs.append(box)

    # Build connection arrows
    conn_svgs = []
    for conn in connections:
        svg = _svg_connection(conn, sections, positions)
        if svg:
            conn_svgs.append(svg)

    sections_markup = "\n    ".join(section_svgs)
    connections_markup = "\n    ".join(conn_svgs)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title} - VideoMind Sketchnote</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Caveat:wght@400;700&display=swap" rel="stylesheet">
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  html, body {{
    height: 100%;
    width: 100%;
  }}
  body {{
    font-family: 'Segoe UI', Arial, sans-serif;
    background: #FFFEF9;
    color: #333;
    display: flex;
    flex-direction: column;
    overflow: auto;
  }}
  header {{
    padding: 16px 24px;
    background: #16213e;
    border-bottom: 2px solid #0f3460;
    display: flex;
    align-items: center;
    justify-content: space-between;
    flex-shrink: 0;
  }}
  header h1 {{
    font-size: 1.3rem;
    font-weight: 600;
    color: #eee;
  }}
  header .badge {{
    background: #e94560;
    color: #fff;
    padding: 4px 12px;
    border-radius: 12px;
    font-size: 0.75rem;
    font-weight: 600;
  }}
  .sketch-container {{
    flex: 1;
    display: flex;
    justify-content: center;
    padding: 20px;
  }}
  svg {{
    max-width: 100%;
    height: auto;
  }}
</style>
</head>
<body>
<header>
  <h1>{title}</h1>
  <span class="badge">VideoMind</span>
</header>
<div class="sketch-container">
  <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 {svg_h}" width="1000" height="{svg_h}">
    <defs>
      <filter id="sketchy" x="-2%" y="-2%" width="104%" height="104%">
        <feTurbulence type="turbulence" baseFrequency="0.03" numOctaves="3" result="noise" seed="2"/>
        <feDisplacementMap in="SourceGraphic" in2="noise" scale="2.5" xChannelSelector="R" yChannelSelector="G"/>
      </filter>
      <marker id="arrowhead" markerWidth="10" markerHeight="7" refX="10" refY="3.5" orient="auto">
        <polygon points="0 0, 10 3.5, 0 7" fill="#888"/>
      </marker>
    </defs>

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
    {sections_markup}
  </svg>
</div>
</body>
</html>"""


def generate_mindmap(
    transcript: str,
    output_dir: str,
    formats: str = "all",
    language: str = "",
) -> dict:
    """Generate sketchnote files from a transcript.

    Args:
        transcript: The full transcript text.
        output_dir: Directory to write output files to.
        formats: "all", "html", "md", or "json".
        language: Detected transcript language (e.g. "Spanish"). Empty or
                  "unknown" means no language instruction is added.

    Returns:
        {"json_path": str, "md_path": str, "html_path": str, "data": dict}
    """
    os.makedirs(output_dir, exist_ok=True)

    print("  Analyzing transcript with Claude...")
    data = _call_claude(transcript, language=language)

    paths = {}

    if formats in ("all", "json"):
        json_path = os.path.join(output_dir, "mindmap.json")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        paths["json_path"] = json_path
        print(f"  Saved: {json_path}")

    if formats in ("all", "md"):
        md_content = _generate_markdown(data)
        md_path = os.path.join(output_dir, "mindmap.md")
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(md_content)
        paths["md_path"] = md_path
        print(f"  Saved: {md_path}")

    if formats in ("all", "html"):
        html_content = _generate_html(data)
        html_path = os.path.join(output_dir, "mindmap.html")
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html_content)
        paths["html_path"] = html_path
        print(f"  Saved: {html_path}")

    paths["data"] = data
    return paths
