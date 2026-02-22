"""Sketchnote generation using Claude API.

Backward-compatible wrapper that delegates to the new formats system.
All public names used by existing code and tests are re-exported here.
"""

from pipeline.formats import generate_visual_format
from pipeline.formats.sketchnote import SketchnoteFormat
from pipeline.formats.base import MAX_TRANSCRIPT_LENGTH  # re-export for tests

_sketchnote = SketchnoteFormat()

# Re-export prompts so existing code that reads them still works
SYSTEM_PROMPT = _sketchnote.SYSTEM_PROMPT
EXTRACTION_PROMPT = _sketchnote.EXTRACTION_PROMPT


def _call_claude(transcript: str, language: str = "") -> dict:
    """Send transcript to Claude and parse the JSON response."""
    return _sketchnote.call_claude(transcript, language=language)


def _generate_markdown(data: dict) -> str:
    """Generate a Markdown sketchnote summary."""
    return _sketchnote.generate_markdown(data)


def _layout_sections(sections: list) -> tuple:
    """Compute grid positions for sections. Returns (positions, rows, cell_h)."""
    return SketchnoteFormat._layout_sections(sections)


def _svg_connection(conn: dict, sections: list, positions: list) -> str:
    """Generate an SVG path for a connection arrow between two sections."""
    return SketchnoteFormat._svg_connection(conn, sections, positions)


def _generate_html(data: dict) -> str:
    """Generate a self-contained HTML page with an SVG sketchnote."""
    return _sketchnote.generate_html(data)


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
    return generate_visual_format(
        transcript,
        output_dir,
        format_type="sketchnote",
        formats=formats,
        language=language,
    )
