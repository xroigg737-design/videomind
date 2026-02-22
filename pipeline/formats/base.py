"""Base class and shared helpers for visual format generators."""

import json
import os
from abc import ABC, abstractmethod
from xml.sax.saxutils import escape as xml_escape

import anthropic

from config import ANTHROPIC_API_KEY, CLAUDE_MODEL

# Maximum transcript characters to send to Claude (to stay within context limits)
MAX_TRANSCRIPT_LENGTH = 100_000

# Shared color palette
COLORS = ["#4A90D9", "#E67E22", "#2ECC71", "#9B59B6", "#E74C3C", "#1ABC9C", "#F39C12", "#3498DB"]


def _extract_json_from_response(response_text: str) -> dict:
    """Extract JSON from a Claude response, handling markdown code blocks."""
    text = response_text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
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
        text = "\n".join(json_lines)
    return json.loads(text)


def html_page_wrapper(title: str, svg_content: str, svg_h: int) -> str:
    """Wrap SVG content in a full HTML page with Caveat font and sketchy styling."""
    escaped_title = xml_escape(title)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{escaped_title} - VideoMind</title>
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
  <h1>{escaped_title}</h1>
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
    {svg_content}
  </svg>
</div>
</body>
</html>"""


class VisualFormat(ABC):
    """Abstract base for visual format generators."""

    FORMAT_TYPE: str = ""
    SYSTEM_PROMPT: str = ""
    EXTRACTION_PROMPT: str = ""  # must contain {transcript} placeholder
    FILE_PREFIX: str = ""

    def call_claude(self, transcript: str, language: str = "") -> dict:
        """Send transcript to Claude and parse the JSON response."""
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

        if len(transcript) > MAX_TRANSCRIPT_LENGTH:
            transcript = transcript[:MAX_TRANSCRIPT_LENGTH] + "\n\n[...transcript truncated...]"

        prompt = self.EXTRACTION_PROMPT.format(transcript=transcript)
        if language and language != "unknown":
            prompt += (
                f"\n\nIMPORTANT: Write ALL content "
                f"(title, headings, points, connection labels) in {language}."
            )

        message = client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=4096,
            system=self.SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}],
        )

        response_text = message.content[0].text.strip()
        return _extract_json_from_response(response_text)

    @abstractmethod
    def validate(self, data: dict) -> list:
        """Validate extracted data. Returns list of warning strings (empty = valid)."""

    @abstractmethod
    def generate_markdown(self, data: dict) -> str:
        """Generate Markdown representation."""

    @abstractmethod
    def generate_html(self, data: dict) -> str:
        """Generate standalone HTML page with SVG visualization."""

    def generate(
        self,
        transcript: str,
        output_dir: str,
        formats: str = "all",
        language: str = "",
    ) -> dict:
        """Orchestrate: call Claude, validate, write output files.

        Returns dict with json_path, md_path, html_path, data keys.
        """
        os.makedirs(output_dir, exist_ok=True)

        print("  Analyzing transcript with Claude...")
        data = self.call_claude(transcript, language=language)

        warnings = self.validate(data)
        for w in warnings:
            print(f"  Warning: {w}")

        paths = {}
        prefix = self.FILE_PREFIX

        if formats in ("all", "json"):
            json_path = os.path.join(output_dir, f"{prefix}.json")
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            paths["json_path"] = json_path
            print(f"  Saved: {json_path}")

        if formats in ("all", "md"):
            md_content = self.generate_markdown(data)
            md_path = os.path.join(output_dir, f"{prefix}.md")
            with open(md_path, "w", encoding="utf-8") as f:
                f.write(md_content)
            paths["md_path"] = md_path
            print(f"  Saved: {md_path}")

        if formats in ("all", "html"):
            html_content = self.generate_html(data)
            html_path = os.path.join(output_dir, f"{prefix}.html")
            with open(html_path, "w", encoding="utf-8") as f:
                f.write(html_content)
            paths["html_path"] = html_path
            print(f"  Saved: {html_path}")

        paths["data"] = data
        return paths
