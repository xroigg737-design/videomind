"""Visual format registry, dispatcher, and heuristic layout selection.

Provides a unified API to generate any supported visual format from a transcript.
Includes automatic format detection based on content type.
"""

from pipeline.formats.sketchnote import SketchnoteFormat
from pipeline.formats.mindmap_format import MindmapFormat
from pipeline.formats.infografia import InfografiaFormat

FORMAT_REGISTRY = {
    "sketchnote": SketchnoteFormat(),
    "mindmap": MindmapFormat(),
    "infografia": InfografiaFormat(),
}

# Heuristic mapping: content_type → best visual format
_CONTENT_TYPE_TO_FORMAT = {
    "procedural": "infografia",     # Step-by-step → vertical blocks
    "conceptual": "mindmap",        # Abstract ideas → radial map
    "pedagogical": "sketchnote",    # Teaching/inspiration → visual quadrants
}


def detect_best_format(content_type: str) -> str:
    """Heuristic layout selection based on content type.

    Rules:
      - procedural content → Infographic (vertical blocks)
      - conceptual content → Mindmap (radial keyword map)
      - pedagogical content → Sketchnote (visual quadrants)
    """
    return _CONTENT_TYPE_TO_FORMAT.get(content_type, "sketchnote")


def get_format(format_type: str):
    """Return the VisualFormat instance for *format_type*, or raise ValueError."""
    fmt = FORMAT_REGISTRY.get(format_type)
    if fmt is None:
        valid = ", ".join(sorted(FORMAT_REGISTRY))
        raise ValueError(f"Unknown visual format '{format_type}'. Valid: {valid}")
    return fmt


def generate_visual_format(
    transcript: str,
    output_dir: str,
    format_type: str = "sketchnote",
    formats: str = "all",
    language: str = "",
    auto_detect: bool = False,
    dalle_options: dict | None = None,
) -> dict:
    """Generate a visual format from a transcript.

    Args:
        transcript: Full transcript text.
        output_dir: Directory to write output files.
        format_type: One of "sketchnote", "mindmap", "infografia".
        formats: Output file formats — "all", "html", "md", or "json".
        language: Detected language (e.g. "Spanish"). Empty = no hint.
        auto_detect: If True, ignore format_type and auto-select based on content.
        dalle_options: Optional dict with DALL-E generation settings.

    Returns:
        dict with json_path, md_path, html_path, data keys.
    """
    if auto_detect:
        # Run Layer 1 first to detect content type, then choose format
        from pipeline.formats.content_engine import extract_content
        data = extract_content(transcript, language=language)
        content_type = data.get("content_type", "conceptual")
        format_type = detect_best_format(content_type)
        print(f"  Auto-detected format: {format_type} (content_type={content_type})")

    fmt = get_format(format_type)
    return fmt.generate(
        transcript, output_dir, formats=formats, language=language,
        dalle_options=dalle_options,
    )


def generate_sketchnote(transcript: str, output_dir: str, **kwargs) -> dict:
    """Convenience: generate sketchnote format."""
    return generate_visual_format(transcript, output_dir, format_type="sketchnote", **kwargs)


def generate_mindmap_format(transcript: str, output_dir: str, **kwargs) -> dict:
    """Convenience: generate mindmap (tree) format."""
    return generate_visual_format(transcript, output_dir, format_type="mindmap", **kwargs)


def generate_infografia(transcript: str, output_dir: str, **kwargs) -> dict:
    """Convenience: generate infografia format."""
    return generate_visual_format(transcript, output_dir, format_type="infografia", **kwargs)
