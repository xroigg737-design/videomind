"""DALL-E image generation for VideoMind visual formats.

Generates three types of images:
  1. Section icons — 2x2 grid split into individual icons
  2. Companion image — full illustration for the topic
  3. Background texture — subtle pattern for SVG backgrounds

All generation is optional and fails gracefully (returns None on error).
Images are returned as base64 data URIs for embedding in SVG.
"""

import base64
import io
import os
import logging

from config import OPENAI_API_KEY, DALLE_MODEL, DALLE_QUALITY

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Prompt composition
# ---------------------------------------------------------------------------

def _compose_icon_grid_prompt(data: dict) -> str:
    """Build a prompt for a 2x2 grid of section icons."""
    sections = data.get("sections", [])[:4]
    labels = [s.get("label", "") for s in sections]
    while len(labels) < 4:
        labels.append(labels[-1] if labels else "abstract concept")

    return (
        f"A 2x2 grid of 4 simple flat-design icons on a white background. "
        f"Each icon is a minimal, colorful symbol representing one concept. "
        f"Top-left: {labels[0]}. Top-right: {labels[1]}. "
        f"Bottom-left: {labels[2]}. Bottom-right: {labels[3]}. "
        f"Clean vector style, thick outlines, bright colors, "
        f"well-separated quadrants with clear dividing lines. "
        f"No text, no letters, no words, no numbers."
    )


def _compose_companion_prompt(data: dict, format_type: str) -> str:
    """Build a prompt for a companion illustration."""
    title = data.get("title", "")
    central = data.get("central_idea", "")
    sections = data.get("sections", [])[:4]
    topics = ", ".join(s.get("label", "") for s in sections)

    style_map = {
        "sketchnote": "hand-drawn sketch style with warm colors",
        "mindmap": "clean modern infographic style with connected elements",
        "infografia": "professional editorial illustration style",
    }
    style = style_map.get(format_type, "clean modern illustration style")

    return (
        f"An illustration about '{title}': {central}. "
        f"Key topics: {topics}. "
        f"Style: {style}. "
        f"Visually rich, educational, engaging. "
        f"No text, no letters, no words, no numbers."
    )


def _compose_infographic_prompt(data: dict, format_type: str, language: str) -> str:
    """Build a prompt for a full AI-generated infographic image.

    Translates structured content JSON into a detailed visual description
    with format-specific style instructions.
    """
    title = data.get("title", "")
    central = data.get("central_idea", "")
    sections = data.get("sections", [])[:4]

    # Build section descriptions
    section_lines = []
    for i, sec in enumerate(sections, 1):
        label = sec.get("label", "")
        bullets = sec.get("bullets", [])
        bullet_text = "; ".join(b if isinstance(b, str) else b.get("text", "") for b in bullets[:4])
        section_lines.append(f"Section {i}: \"{label}\" — {bullet_text}")
    sections_desc = "\n".join(section_lines)

    # Practice plan if present
    practice = data.get("practice_plan", {})
    practice_desc = ""
    if practice:
        steps = practice.get("steps", [])
        if steps:
            step_texts = [s if isinstance(s, str) else s.get("text", "") for s in steps[:3]]
            practice_desc = f'\nPractice plan: "{practice.get("title", "Practice")}": {"; ".join(step_texts)}'

    # Examples if present
    examples = data.get("examples", [])
    examples_desc = ""
    if examples:
        ex_texts = [e if isinstance(e, str) else e.get("text", "") for e in examples[:3]]
        examples_desc = f"\nExamples: {'; '.join(ex_texts)}"

    # Format-specific style
    style_instructions = {
        "infografia": (
            "Style: Professional vertical infographic poster with watercolor painted header banner, "
            "soft pastel color palette, cute cartoon illustrations for each section, "
            "decorative borders and dividers, rounded content boxes with subtle shadows. "
            "Layout: Vertical poster format. Title at top in large decorative text over watercolor splash. "
            "Sections flow top to bottom, each with its own illustrated icon and colored box. "
            "Overall feel: warm, educational, visually rich like a classroom poster."
        ),
        "sketchnote": (
            "Style: Hand-drawn sketchnote on white paper with brush-stroke lettering, "
            "doodle illustrations, organic flowing layout with arrows and connectors, "
            "marker-style text in varied sizes, small cartoon characters and icons. "
            "Layout: Landscape notebook page. Title in large hand-lettered text at top center. "
            "Sections spread organically across the page connected by arrows and doodle lines. "
            "Overall feel: personal notebook, hand-crafted, like visual meeting notes."
        ),
        "mindmap": (
            "Style: Clean modern mind map diagram with a central node and radiating branches, "
            "each branch a different color, clean sans-serif text, simple geometric icons, "
            "thin connecting lines, minimalist flat design. "
            "Layout: Landscape format. Central idea in the middle circle, branches radiating outward. "
            "Overall feel: clean, professional, organized radial diagram."
        ),
    }
    style = style_instructions.get(format_type, style_instructions["infografia"])

    # Language instruction
    lang_name = {
        "ca": "Catalan", "es": "Spanish", "en": "English",
        "fr": "French", "de": "German", "it": "Italian", "pt": "Portuguese",
    }.get(language, language if language else "the same language as the content")
    lang_instruction = (
        f"CRITICAL: All visible text in the image MUST be written in {lang_name}. "
        f"Reproduce the exact text provided below — do not translate, rephrase, or abbreviate."
    )

    return (
        f"Create a complete educational infographic image.\n\n"
        f"{lang_instruction}\n\n"
        f"Title: \"{title}\"\n"
        f"Central idea: \"{central}\"\n"
        f"{sections_desc}"
        f"{examples_desc}"
        f"{practice_desc}\n\n"
        f"{style}\n\n"
        f"IMPORTANT: Include ALL the text content listed above in the image, "
        f"spelled exactly as written. The text is educational content and must be readable."
    )


def _compose_background_prompt(data: dict) -> str:
    """Build a prompt for a subtle background texture."""
    title = data.get("title", "abstract")
    return (
        f"A very subtle, seamless background texture pattern inspired by "
        f"the theme '{title}'. Extremely light and muted colors, "
        f"almost white with faint geometric or organic patterns. "
        f"Suitable as a low-opacity background. Tileable. "
        f"No text, no letters, no words, no numbers."
    )


# ---------------------------------------------------------------------------
# API interaction
# ---------------------------------------------------------------------------

def _call_dalle(prompt: str, size: str = "1024x1024") -> bytes | None:
    """Call the DALL-E API and return raw PNG bytes, or None on failure."""
    if not OPENAI_API_KEY:
        print(f"    {DALLE_MODEL}: OPENAI_API_KEY not set, skipping.")
        return None

    try:
        from openai import OpenAI

        client = OpenAI(api_key=OPENAI_API_KEY)
        response = client.images.generate(
            model=DALLE_MODEL,
            prompt=prompt,
            size=size,
            quality=DALLE_QUALITY,
            n=1,
        )
        b64_data = response.data[0].b64_json
        return base64.b64decode(b64_data)
    except Exception as e:
        print(f"    {DALLE_MODEL} API error: {e}")
        return None


# ---------------------------------------------------------------------------
# Image processing
# ---------------------------------------------------------------------------

def _split_grid_image(image_bytes: bytes, count: int = 4) -> list[bytes]:
    """Split a 2x2 grid image into individual icon images."""
    try:
        from PIL import Image

        img = Image.open(io.BytesIO(image_bytes))
        w, h = img.size
        half_w, half_h = w // 2, h // 2

        # 2x2 grid positions: top-left, top-right, bottom-left, bottom-right
        boxes = [
            (0, 0, half_w, half_h),
            (half_w, 0, w, half_h),
            (0, half_h, half_w, h),
            (half_w, half_h, w, h),
        ]

        icons = []
        for i in range(min(count, 4)):
            cropped = img.crop(boxes[i])
            buf = io.BytesIO()
            cropped.save(buf, format="PNG")
            icons.append(buf.getvalue())

        return icons
    except Exception as e:
        logger.warning("Failed to split grid image: %s", e)
        return []


def image_to_base64_uri(image_bytes: bytes) -> str:
    """Convert raw PNG bytes to a data URI string."""
    b64 = base64.b64encode(image_bytes).decode("ascii")
    return f"data:image/png;base64,{b64}"


# ---------------------------------------------------------------------------
# High-level generation functions
# ---------------------------------------------------------------------------

def generate_section_icons(data: dict, output_dir: str) -> dict | None:
    """Generate section icons via a single 2x2 grid DALL-E call.

    Returns dict with 'icon_uris' (list of data URIs) and 'grid_path',
    or None on failure.
    """
    prompt = _compose_icon_grid_prompt(data)
    print(f"    {DALLE_MODEL}: Generating section icons...")
    grid_bytes = _call_dalle(prompt, size="1024x1024")
    if grid_bytes is None:
        return None

    # Save the grid image
    grid_path = os.path.join(output_dir, "dalle_icon_grid.png")
    with open(grid_path, "wb") as f:
        f.write(grid_bytes)

    # Split into individual icons
    section_count = min(len(data.get("sections", [])), 4)
    icon_images = _split_grid_image(grid_bytes, section_count)
    if not icon_images:
        return None

    # Save individual icons and create URIs
    icon_uris = []
    icon_paths = []
    for i, icon_bytes in enumerate(icon_images):
        path = os.path.join(output_dir, f"dalle_icon_{i}.png")
        with open(path, "wb") as f:
            f.write(icon_bytes)
        icon_uris.append(image_to_base64_uri(icon_bytes))
        icon_paths.append(path)

    print(f"    {DALLE_MODEL}: {len(icon_uris)} section icons generated.")
    return {
        "icon_uris": icon_uris,
        "icon_paths": icon_paths,
        "grid_path": grid_path,
    }


def generate_companion_image(
    data: dict, format_type: str, output_dir: str
) -> dict | None:
    """Generate a full companion illustration.

    Returns dict with 'image_uri' and 'image_path', or None on failure.
    """
    prompt = _compose_companion_prompt(data, format_type)
    print(f"    {DALLE_MODEL}: Generating companion image...")
    image_bytes = _call_dalle(prompt, size="1536x1024")
    if image_bytes is None:
        return None

    image_path = os.path.join(output_dir, f"dalle_companion_{format_type}.png")
    with open(image_path, "wb") as f:
        f.write(image_bytes)

    print(f"    {DALLE_MODEL}: Companion image generated.")
    return {
        "image_uri": image_to_base64_uri(image_bytes),
        "image_path": image_path,
    }


def generate_background(data: dict, output_dir: str) -> dict | None:
    """Generate a subtle background texture.

    Returns dict with 'bg_uri' and 'bg_path', or None on failure.
    """
    prompt = _compose_background_prompt(data)
    print(f"    {DALLE_MODEL}: Generating background texture...")
    bg_bytes = _call_dalle(prompt, size="1024x1024")
    if bg_bytes is None:
        return None

    bg_path = os.path.join(output_dir, "dalle_background.png")
    with open(bg_path, "wb") as f:
        f.write(bg_bytes)

    print(f"    {DALLE_MODEL}: Background texture generated.")
    return {
        "bg_uri": image_to_base64_uri(bg_bytes),
        "bg_path": bg_path,
    }


def generate_full_infographic(
    data: dict, format_type: str, output_dir: str, language: str = ""
) -> dict | None:
    """Generate a complete AI infographic as a single image.

    Returns dict with 'image_path', 'image_uri', 'size', or None on failure.
    """
    prompt = _compose_infographic_prompt(data, format_type, language)

    # Size by format: vertical for infografia, landscape for others
    if format_type == "infografia":
        size = "1024x1536"
    else:
        size = "1536x1024"

    print(f"    {DALLE_MODEL}: Generating full {format_type} infographic ({size})...")
    image_bytes = _call_dalle(prompt, size=size)
    if image_bytes is None:
        return None

    image_path = os.path.join(output_dir, f"dalle_infographic_{format_type}.png")
    with open(image_path, "wb") as f:
        f.write(image_bytes)

    print(f"    {DALLE_MODEL}: Full infographic generated.")
    return {
        "image_path": image_path,
        "image_uri": image_to_base64_uri(image_bytes),
        "size": size,
    }


def generate_all_images(
    data: dict,
    format_type: str,
    output_dir: str,
    icons: bool = True,
    companion: bool = False,
    background: bool = False,
    full_infographic: bool = False,
    language: str = "",
) -> dict:
    """Orchestrate all DALL-E image generation.

    Args:
        data: Unified content JSON from Layer 2.
        format_type: Visual format type (sketchnote, mindmap, infografia).
        output_dir: Directory to save generated images.
        icons: Generate section icons (default True when DALL-E enabled).
        companion: Generate companion illustration.
        background: Generate background texture.
        full_infographic: Generate a single AI image for the entire infographic.
        language: Content language code for text accuracy.

    Returns:
        dict with keys 'icons', 'companion', 'background', 'full_infographic'
        (each may be None).
    """
    os.makedirs(output_dir, exist_ok=True)
    result = {"icons": None, "companion": None, "background": None, "full_infographic": None}

    # Full infographic mode: one call replaces all component images
    if full_infographic:
        result["full_infographic"] = generate_full_infographic(
            data, format_type, output_dir, language=language
        )
        if result["full_infographic"]:
            # Success — skip component generation
            return result
        print(f"    {DALLE_MODEL}: Full infographic failed, falling back to component images.")

    if icons:
        result["icons"] = generate_section_icons(data, output_dir)

    if companion:
        result["companion"] = generate_companion_image(
            data, format_type, output_dir
        )

    if background:
        result["background"] = generate_background(data, output_dir)

    return result
