"""Base class and shared helpers for visual format generators.

Refactored 3-layer pipeline:
  Layer 1 — Content Engine:    LLM → unified JSON (no HTML/SVG)
  Layer 2 — Content Reducer:   Shorten, de-duplicate, enforce limits
  Layer 3 — Layout Engine:     Format-specific SVG rendering

Quality check runs between Layer 2 and Layer 3.
"""

import json
import os
from abc import ABC, abstractmethod
from xml.sax.saxutils import escape as xml_escape

import anthropic

from config import ANTHROPIC_API_KEY, CLAUDE_MODEL, DALLE_MODEL

# Maximum transcript characters to send to Claude (to stay within context limits)
MAX_TRANSCRIPT_LENGTH = 100_000

# Maximum auto-retry attempts before accepting best result
MAX_RETRIES = 2

# ---------------------------------------------------------------------------
# Design Tokens (shared across all formats)
# ---------------------------------------------------------------------------

DESIGN_TOKENS = {
    "primary": "#2D5BFF",
    "background": "#FFFFFF",
    "accent": "#111827",
    "accent_light": "#6B7280",
    "border_radius": 12,
    "spacing": 24,
    "spacing_lg": 32,
    "spacing_xl": 48,
    "font_heading": "'Inter', -apple-system, BlinkMacSystemFont, sans-serif",
    "font_body": "'Inter', -apple-system, BlinkMacSystemFont, sans-serif",
    "font_sketch": "'Caveat', 'Segoe Print', cursive",
}

# Section color palette — clean, professional, distinct
SECTION_COLORS = ["#2D5BFF", "#10B981", "#F59E0B", "#EF4444"]

# Legacy palettes (kept for backward compat)
COLORS = ["#4A90D9", "#E67E22", "#2ECC71", "#9B59B6", "#E74C3C", "#1ABC9C", "#F39C12", "#3498DB"]
EXECUTIVE_COLORS = ["#5B8DEF", "#F2994A", "#6FCF97", "#BB6BD9", "#EB5757"]
INFOGRAFIA_COLORS = ["#2D5BFF", "#00B894", "#FDCB6E", "#E17055", "#6C5CE7"]


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


def lighten_color(hex_color: str, factor: float) -> str:
    """Lighten a hex color toward white by the given factor (0-1)."""
    hex_color = hex_color.lstrip("#")
    r = int(hex_color[0:2], 16)
    g = int(hex_color[2:4], 16)
    b = int(hex_color[4:6], 16)
    r = int(r + (255 - r) * factor)
    g = int(g + (255 - g) * factor)
    b = int(b + (255 - b) * factor)
    return f"#{r:02x}{g:02x}{b:02x}"


# ---------------------------------------------------------------------------
# HTML page wrappers (Layer 3 shared templates)
# ---------------------------------------------------------------------------

def html_page_clean(title: str, svg_content: str, svg_w: int, svg_h: int) -> str:
    """Wrap SVG in a clean, professional HTML page using design tokens."""
    escaped_title = xml_escape(title)
    font = DESIGN_TOKENS["font_heading"]
    bg = DESIGN_TOKENS["background"]
    accent = DESIGN_TOKENS["accent"]

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{escaped_title} - VideoMind</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
<link href="https://fonts.googleapis.com/css2?family=Caveat:wght@400;700&display=swap" rel="stylesheet">
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  html, body {{ height: 100%; width: 100%; }}
  body {{
    font-family: {font};
    background: {bg};
    color: {accent};
    display: flex;
    flex-direction: column;
    align-items: center;
    overflow: auto;
  }}
  .container {{
    flex: 1;
    display: flex;
    justify-content: center;
    align-items: flex-start;
    padding: 40px 20px;
    width: 100%;
    max-width: 1400px;
  }}
  svg {{ max-width: 100%; height: auto; }}
</style>
</head>
<body>
<div class="container">
  <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {svg_w} {svg_h}" width="{svg_w}" height="{svg_h}">
    {svg_content}
  </svg>
</div>
</body>
</html>"""


def html_page_sketch(title: str, svg_content: str, svg_h: int) -> str:
    """Wrap SVG in a whiteboard/notebook-style HTML page for sketchnotes."""
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
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  html, body {{ height: 100%; width: 100%; }}
  body {{
    font-family: 'Caveat', 'Segoe Print', cursive;
    background: #FAFAFA;
    color: #222;
    display: flex;
    flex-direction: column;
    align-items: center;
    overflow: auto;
  }}
  .container {{
    flex: 1;
    display: flex;
    justify-content: center;
    align-items: flex-start;
    padding: 30px 20px;
    width: 100%;
    max-width: 1100px;
  }}
  svg {{ max-width: 100%; height: auto; }}
</style>
</head>
<body>
<div class="container">
  <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 {svg_h}" width="1000" height="{svg_h}">
    <defs>
      <filter id="sketchy" x="-2%" y="-2%" width="104%" height="104%">
        <feTurbulence type="turbulence" baseFrequency="0.02" numOctaves="4" result="noise" seed="3"/>
        <feDisplacementMap in="SourceGraphic" in2="noise" scale="2" xChannelSelector="R" yChannelSelector="G"/>
      </filter>
    </defs>
    {svg_content}
  </svg>
</div>
</body>
</html>"""


# Legacy wrappers kept for backward compat
def html_page_wrapper(title: str, svg_content: str, svg_h: int) -> str:
    return html_page_sketch(title, svg_content, svg_h)


def html_page_executive(title: str, svg_content: str, svg_w: int, svg_h: int) -> str:
    return html_page_clean(title, svg_content, svg_w, svg_h)


def html_page_image(title: str, image_uri: str, width: int, height: int) -> str:
    """Wrap an AI-generated infographic image in a responsive HTML page."""
    escaped_title = xml_escape(title)
    font = DESIGN_TOKENS["font_heading"]
    bg = DESIGN_TOKENS["background"]

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{escaped_title} - VideoMind</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  html, body {{ height: 100%; width: 100%; }}
  body {{
    font-family: {font};
    background: {bg};
    display: flex;
    flex-direction: column;
    align-items: center;
    overflow: auto;
  }}
  .container {{
    flex: 1;
    display: flex;
    justify-content: center;
    align-items: flex-start;
    padding: 40px 20px;
    width: 100%;
    max-width: 1400px;
  }}
  .infographic-img {{
    max-width: 100%;
    height: auto;
    border-radius: 12px;
    box-shadow: 0 4px 24px rgba(0, 0, 0, 0.12);
  }}
</style>
</head>
<body>
<div class="container">
  <img src="{image_uri}" alt="{escaped_title}" class="infographic-img"
       width="{width}" height="{height}">
</div>
</body>
</html>"""


# ---------------------------------------------------------------------------
# Abstract base class
# ---------------------------------------------------------------------------

class VisualFormat(ABC):
    """Abstract base for visual format generators.

    Subclasses must define:
      FORMAT_TYPE  — e.g. "mindmap", "sketchnote", "infografia"
      FILE_PREFIX  — output filename prefix
    """

    FORMAT_TYPE: str = ""
    FILE_PREFIX: str = ""

    # Legacy attributes (kept for backward compat)
    TRANSFORM_SYSTEM: str = ""
    TRANSFORM_PROMPT: str = ""
    SYSTEM_PROMPT: str = ""
    EXTRACTION_PROMPT: str = ""

    # -----------------------------------------------------------------
    # Abstract methods (Layer 3 — Layout Engine)
    # -----------------------------------------------------------------

    @abstractmethod
    def generate_markdown(self, data: dict) -> str:
        """Generate Markdown representation from unified content JSON."""

    @abstractmethod
    def generate_html(self, data: dict, dalle_images: dict | None = None) -> str:
        """Generate standalone HTML page with SVG visualization from unified content JSON.

        Args:
            data: Unified content JSON from Layer 2.
            dalle_images: Optional dict from dalle_generator.generate_all_images()
                          with keys 'icons', 'companion', 'background'.
        """

    # -----------------------------------------------------------------
    # Orchestration — 3-layer pipeline
    # -----------------------------------------------------------------

    def generate(
        self,
        transcript: str,
        output_dir: str,
        formats: str = "all",
        language: str = "",
        dalle_options: dict | None = None,
    ) -> dict:
        """Orchestrate the 3-layer pipeline: extract → reduce → render.

        Args:
            dalle_options: Optional dict with keys 'enabled', 'icons', 'companion',
                           'background'. When enabled, runs DALL-E generation between
                           Layer 2 and Layer 3.

        Returns dict with json_path, md_path, html_path, data keys.
        """
        from pipeline.formats.content_engine import (
            extract_content,
            validate_content,
            retry_content,
        )
        from pipeline.formats.quality_check import ensure_quality

        os.makedirs(output_dir, exist_ok=True)

        # ── Layer 1: Content Engine — LLM extracts unified JSON ──
        print("  Layer 1: Extracting content structure...")
        data = extract_content(transcript, language=language)

        print(f"    Title: {data.get('title', '?')}")
        print(f"    Type: {data.get('content_type', '?')}")
        print(f"    Sections: {len(data.get('sections', []))}")

        # Validate and auto-retry if needed
        violations = validate_content(data)
        attempt = 0
        while violations and attempt < MAX_RETRIES:
            attempt += 1
            for v in violations:
                print(f"    Violation: {v}")
            print(f"    Auto-fixing (attempt {attempt}/{MAX_RETRIES})...")
            data = retry_content(data, violations, language=language)
            violations = validate_content(data)

        if violations:
            for v in violations:
                print(f"    Remaining warning: {v}")
        else:
            print("    Content extraction validated.")

        # ── Layer 2: Content Reducer + Quality Check ──
        print("  Layer 2: Reducing content and checking quality...")
        data = ensure_quality(data)

        from pipeline.formats.content_reducer import count_visible_words
        word_count = count_visible_words(data)
        print(f"    Visible words: {word_count}")

        # ── Image Layer: DALL-E generation (optional) ──
        dalle_images = None
        if dalle_options and dalle_options.get("enabled"):
            from config import validate_dalle_config
            if validate_dalle_config():
                from pipeline.dalle_generator import generate_all_images
                if dalle_options.get("full_infographic"):
                    print("  Image Layer: Generating full AI infographic...")
                else:
                    print(f"  Image Layer: Generating {DALLE_MODEL} images...")
                dalle_images = generate_all_images(
                    data,
                    format_type=self.FORMAT_TYPE,
                    output_dir=output_dir,
                    icons=dalle_options.get("icons", True),
                    companion=dalle_options.get("companion", False),
                    background=dalle_options.get("background", False),
                    full_infographic=dalle_options.get("full_infographic", False),
                    language=language,
                )
                # Report results
                if dalle_images:
                    generated = [k for k in ("icons", "companion", "background", "full_infographic")
                                 if dalle_images.get(k)]
                    if generated:
                        labels = {"full_infographic": "infografia IA", "icons": "icones",
                                  "companion": "il·lustracio", "background": "textura"}
                        names = [labels.get(k, k) for k in generated]
                        print(f"    Imatges generades: {', '.join(names)}")
                    else:
                        print("    Generacio d'imatges fallida, usant icones SVG.")

        # ── Layer 3: Layout Engine — format-specific rendering ──
        print(f"  Layer 3: Rendering {self.FORMAT_TYPE} layout...")

        # ── Write output files ──
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
            # Always render the SVG-based layout for the main HTML file.
            # The DALL-E full infographic (if generated) is saved separately
            # as dalle_infographic_<format>.png and shown in its own viewer section.
            html_content = self.generate_html(data, dalle_images=dalle_images)
            html_path = os.path.join(output_dir, f"{prefix}.html")
            with open(html_path, "w", encoding="utf-8") as f:
                f.write(html_content)
            paths["html_path"] = html_path
            print(f"  Saved: {html_path}")

        paths["data"] = data
        return paths

    # -----------------------------------------------------------------
    # Legacy methods (kept for backward compat)
    # -----------------------------------------------------------------

    def validate(self, data: dict) -> list:
        """Legacy validate — now handled by quality_check module."""
        return []

    def transform_from_model(self, structural_model: dict, language: str = "") -> dict:
        """Legacy Phase 3 transform. Kept for backward compat."""
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        model_json = json.dumps(structural_model, indent=2, ensure_ascii=False)
        prompt = self.TRANSFORM_PROMPT.format(structural_model=model_json)
        if language and language != "unknown":
            prompt += f"\n\nIMPORTANT: Write ALL content in {language}."
        message = client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=4096,
            system=self.TRANSFORM_SYSTEM,
            messages=[{"role": "user", "content": prompt}],
        )
        return _extract_json_from_response(message.content[0].text.strip())

    def call_claude(self, transcript: str, language: str = "") -> dict:
        """Legacy single-call path."""
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        if len(transcript) > MAX_TRANSCRIPT_LENGTH:
            transcript = transcript[:MAX_TRANSCRIPT_LENGTH] + "\n\n[...transcript truncated...]"
        prompt = self.EXTRACTION_PROMPT.format(transcript=transcript)
        if language and language != "unknown":
            prompt += f"\n\nIMPORTANT: Write ALL content in {language}."
        message = client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=4096,
            system=self.SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}],
        )
        return _extract_json_from_response(message.content[0].text.strip())
