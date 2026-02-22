"""Visual format registry and dispatcher.

Provides a unified API to generate any supported visual format from a transcript.
"""

from pipeline.formats.sketchnote import SketchnoteFormat
from pipeline.formats.mindmap_format import MindmapFormat
from pipeline.formats.infografia import InfografiaFormat

FORMAT_REGISTRY = {
    "sketchnote": SketchnoteFormat(),
    "mindmap": MindmapFormat(),
    "infografia": InfografiaFormat(),
}


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
) -> dict:
    """Generate a visual format from a transcript.

    Args:
        transcript: Full transcript text.
        output_dir: Directory to write output files.
        format_type: One of "sketchnote", "mindmap", "infografia".
        formats: Output file formats — "all", "html", "md", or "json".
        language: Detected language (e.g. "Spanish"). Empty = no hint.

    Returns:
        dict with json_path, md_path, html_path, data keys.
    """
    fmt = get_format(format_type)
    return fmt.generate(transcript, output_dir, formats=formats, language=language)


def generate_sketchnote(transcript: str, output_dir: str, **kwargs) -> dict:
    """Convenience: generate sketchnote format."""
    return generate_visual_format(transcript, output_dir, format_type="sketchnote", **kwargs)


def generate_mindmap_format(transcript: str, output_dir: str, **kwargs) -> dict:
    """Convenience: generate mindmap (tree) format."""
    return generate_visual_format(transcript, output_dir, format_type="mindmap", **kwargs)


def generate_infografia(transcript: str, output_dir: str, **kwargs) -> dict:
    """Convenience: generate infografia format."""
    return generate_visual_format(transcript, output_dir, format_type="infografia", **kwargs)
