"""Image classifier for visual format detection using Claude Vision API."""

import base64
import json

import anthropic

from config import ANTHROPIC_API_KEY, CLAUDE_MODEL
from pipeline.formats.base import _extract_json_from_response

CLASSIFICATION_PROMPT = """Analyze this image and classify its visual format type.

The possible types are:
- **sketchnote**: Visual note with titled sections/blocks, icons, illustrations,
  bullet points, colored headers, and a closing phrase. Grid or flow layout.
- **mindmap**: Tree/radial diagram with a central node and branching hierarchy.
  Nodes connected by lines/arrows radiating outward.
- **infografia**: Vertical panel layout with exactly 3 sequential sections
  (typically Problem/Method/Result), a headline, and a closing quote.

Return ONLY valid JSON:
{
  "visual_type": "sketchnote" | "mindmap" | "infografia",
  "confidence": "high" | "medium" | "low",
  "reasoning": "Brief explanation of why this classification"
}
"""


def classify_image(image_path: str) -> dict:
    """Classify a visual image into sketchnote/mindmap/infografia."""
    with open(image_path, "rb") as f:
        image_data = base64.standard_b64encode(f.read()).decode("utf-8")

    ext = image_path.rsplit(".", 1)[-1].lower()
    media_type = {
        "png": "image/png",
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
    }.get(ext, "image/png")

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    message = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=256,
        messages=[{
            "role": "user",
            "content": [
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": media_type,
                        "data": image_data,
                    },
                },
                {"type": "text", "text": CLASSIFICATION_PROMPT},
            ],
        }],
    )

    return _extract_json_from_response(message.content[0].text)
