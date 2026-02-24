"""Tests for DALL-E image generation module (pipeline.dalle_generator).

All API calls are mocked — no actual DALL-E calls are made.
"""

import base64
import io
import os
import sys
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


# ---------------------------------------------------------------------------
# Sample data fixture
# ---------------------------------------------------------------------------

SAMPLE_DATA = {
    "title": "Neural Networks",
    "central_idea": "Deep learning transforms AI",
    "content_type": "conceptual",
    "sections": [
        {"label": "Architecture", "bullets": ["Layer organization", "Deep networks"], "example": ""},
        {"label": "Training", "bullets": ["Backpropagation", "Gradient descent"], "example": ""},
        {"label": "Data Flow", "bullets": ["Forward pass", "Loss computation"], "example": ""},
        {"label": "Deployment", "bullets": ["Scale models", "Monitor drift"], "example": ""},
    ],
}


def _make_test_png(width=64, height=64, color=(255, 0, 0)):
    """Create a minimal test PNG image using Pillow."""
    from PIL import Image
    img = Image.new("RGB", (width, height), color)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


# ---------------------------------------------------------------------------
# Prompt composition tests
# ---------------------------------------------------------------------------


class TestPromptComposition:
    def test_icon_grid_prompt_contains_labels(self):
        from pipeline.dalle_generator import _compose_icon_grid_prompt
        prompt = _compose_icon_grid_prompt(SAMPLE_DATA)
        assert "Architecture" in prompt
        assert "Training" in prompt
        assert "Data Flow" in prompt
        assert "Deployment" in prompt
        assert "no text" in prompt.lower()

    def test_icon_grid_prompt_pads_to_four(self):
        from pipeline.dalle_generator import _compose_icon_grid_prompt
        data = {"sections": [{"label": "Only One"}]}
        prompt = _compose_icon_grid_prompt(data)
        # Should still reference 4 quadrants
        assert "Top-left" in prompt
        assert "Bottom-right" in prompt

    def test_companion_prompt_includes_style(self):
        from pipeline.dalle_generator import _compose_companion_prompt
        prompt = _compose_companion_prompt(SAMPLE_DATA, "sketchnote")
        assert "hand-drawn" in prompt
        assert "Neural Networks" in prompt
        assert "no text" in prompt.lower()

    def test_companion_prompt_different_styles(self):
        from pipeline.dalle_generator import _compose_companion_prompt
        for fmt, expected in [
            ("mindmap", "infographic"),
            ("infografia", "editorial"),
        ]:
            prompt = _compose_companion_prompt(SAMPLE_DATA, fmt)
            assert expected in prompt

    def test_background_prompt(self):
        from pipeline.dalle_generator import _compose_background_prompt
        prompt = _compose_background_prompt(SAMPLE_DATA)
        assert "Neural Networks" in prompt
        assert "subtle" in prompt.lower()
        assert "no text" in prompt.lower()


# ---------------------------------------------------------------------------
# Image processing tests
# ---------------------------------------------------------------------------


class TestImageProcessing:
    def test_image_to_base64_uri(self):
        from pipeline.dalle_generator import image_to_base64_uri
        raw = b"\x89PNG\r\n\x1a\ntest"
        uri = image_to_base64_uri(raw)
        assert uri.startswith("data:image/png;base64,")
        decoded = base64.b64decode(uri.split(",")[1])
        assert decoded == raw

    def test_split_grid_image(self):
        from pipeline.dalle_generator import _split_grid_image
        png = _make_test_png(100, 100)
        icons = _split_grid_image(png, 4)
        assert len(icons) == 4
        # Each icon should be valid PNG bytes
        for icon_bytes in icons:
            assert icon_bytes[:4] == b"\x89PNG"

    def test_split_grid_fewer_than_four(self):
        from pipeline.dalle_generator import _split_grid_image
        png = _make_test_png(100, 100)
        icons = _split_grid_image(png, 2)
        assert len(icons) == 2

    def test_split_grid_invalid_bytes(self):
        from pipeline.dalle_generator import _split_grid_image
        icons = _split_grid_image(b"not an image", 4)
        assert icons == []


# ---------------------------------------------------------------------------
# API call tests (mocked)
# ---------------------------------------------------------------------------


class TestCallDalle:
    @patch("pipeline.dalle_generator.OPENAI_API_KEY", "test-key")
    def test_call_dalle_success(self):
        from pipeline.dalle_generator import _call_dalle

        # Prepare mock
        png_bytes = _make_test_png()
        b64_data = base64.b64encode(png_bytes).decode()

        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.data = [MagicMock(b64_json=b64_data)]
        mock_client.images.generate.return_value = mock_response

        mock_openai_cls = MagicMock(return_value=mock_client)
        mock_openai_module = MagicMock(OpenAI=mock_openai_cls)

        with patch.dict("sys.modules", {"openai": mock_openai_module}):
            result = _call_dalle("test prompt")

        assert result == png_bytes

    @patch("pipeline.dalle_generator.OPENAI_API_KEY", "")
    def test_call_dalle_no_api_key(self):
        from pipeline.dalle_generator import _call_dalle
        result = _call_dalle("test prompt")
        assert result is None

    @patch("pipeline.dalle_generator.OPENAI_API_KEY", "test-key")
    def test_call_dalle_api_error(self):
        from pipeline.dalle_generator import _call_dalle

        mock_openai_module = MagicMock()
        mock_openai_module.OpenAI.side_effect = Exception("API error")

        with patch.dict("sys.modules", {"openai": mock_openai_module}):
            result = _call_dalle("test prompt")
        assert result is None


# ---------------------------------------------------------------------------
# High-level generation tests (mocked)
# ---------------------------------------------------------------------------


class TestGenerateSectionIcons:
    @patch("pipeline.dalle_generator._call_dalle")
    def test_generates_icons(self, mock_call, tmp_path):
        from pipeline.dalle_generator import generate_section_icons

        mock_call.return_value = _make_test_png(100, 100)
        result = generate_section_icons(SAMPLE_DATA, str(tmp_path))

        assert result is not None
        assert len(result["icon_uris"]) == 4
        assert all(uri.startswith("data:image/png;base64,") for uri in result["icon_uris"])
        assert os.path.exists(result["grid_path"])
        assert len(result["icon_paths"]) == 4

    @patch("pipeline.dalle_generator._call_dalle")
    def test_returns_none_on_failure(self, mock_call, tmp_path):
        from pipeline.dalle_generator import generate_section_icons

        mock_call.return_value = None
        result = generate_section_icons(SAMPLE_DATA, str(tmp_path))
        assert result is None


class TestGenerateCompanionImage:
    @patch("pipeline.dalle_generator._call_dalle")
    def test_generates_companion(self, mock_call, tmp_path):
        from pipeline.dalle_generator import generate_companion_image

        png = _make_test_png(200, 100)
        mock_call.return_value = png
        result = generate_companion_image(SAMPLE_DATA, "sketchnote", str(tmp_path))

        assert result is not None
        assert result["image_uri"].startswith("data:image/png;base64,")
        assert os.path.exists(result["image_path"])
        assert "dalle_companion_sketchnote.png" in result["image_path"]

    @patch("pipeline.dalle_generator._call_dalle")
    def test_returns_none_on_failure(self, mock_call, tmp_path):
        from pipeline.dalle_generator import generate_companion_image

        mock_call.return_value = None
        result = generate_companion_image(SAMPLE_DATA, "mindmap", str(tmp_path))
        assert result is None


class TestGenerateBackground:
    @patch("pipeline.dalle_generator._call_dalle")
    def test_generates_background(self, mock_call, tmp_path):
        from pipeline.dalle_generator import generate_background

        mock_call.return_value = _make_test_png()
        result = generate_background(SAMPLE_DATA, str(tmp_path))

        assert result is not None
        assert result["bg_uri"].startswith("data:image/png;base64,")
        assert os.path.exists(result["bg_path"])

    @patch("pipeline.dalle_generator._call_dalle")
    def test_returns_none_on_failure(self, mock_call, tmp_path):
        from pipeline.dalle_generator import generate_background

        mock_call.return_value = None
        result = generate_background(SAMPLE_DATA, str(tmp_path))
        assert result is None


class TestGenerateAllImages:
    @patch("pipeline.dalle_generator._call_dalle")
    def test_all_enabled(self, mock_call, tmp_path):
        from pipeline.dalle_generator import generate_all_images

        mock_call.return_value = _make_test_png(100, 100)
        result = generate_all_images(
            SAMPLE_DATA, "sketchnote", str(tmp_path),
            icons=True, companion=True, background=True,
        )

        assert result["icons"] is not None
        assert result["companion"] is not None
        assert result["background"] is not None

    @patch("pipeline.dalle_generator._call_dalle")
    def test_only_icons(self, mock_call, tmp_path):
        from pipeline.dalle_generator import generate_all_images

        mock_call.return_value = _make_test_png(100, 100)
        result = generate_all_images(
            SAMPLE_DATA, "sketchnote", str(tmp_path),
            icons=True, companion=False, background=False,
        )

        assert result["icons"] is not None
        assert result["companion"] is None
        assert result["background"] is None
        # Only one API call (icons grid)
        assert mock_call.call_count == 1

    @patch("pipeline.dalle_generator._call_dalle")
    def test_none_enabled(self, mock_call, tmp_path):
        from pipeline.dalle_generator import generate_all_images

        result = generate_all_images(
            SAMPLE_DATA, "sketchnote", str(tmp_path),
            icons=False, companion=False, background=False,
        )

        assert result["icons"] is None
        assert result["companion"] is None
        assert result["background"] is None
        mock_call.assert_not_called()


# ---------------------------------------------------------------------------
# Format integration tests (DALL-E images in HTML output)
# ---------------------------------------------------------------------------


class TestFormatIntegrationWithDalle:
    """Test that format generators accept and use dalle_images parameter."""

    def _make_dalle_images(self):
        """Create a mock dalle_images dict."""
        png = _make_test_png(50, 50)
        from pipeline.dalle_generator import image_to_base64_uri
        uri = image_to_base64_uri(png)
        return {
            "icons": {"icon_uris": [uri, uri, uri, uri], "icon_paths": [], "grid_path": ""},
            "companion": {"image_uri": uri, "image_path": ""},
            "background": {"bg_uri": uri, "bg_path": ""},
        }

    def test_sketchnote_with_dalle_icons(self):
        from pipeline.formats.sketchnote import SketchnoteFormat
        fmt = SketchnoteFormat()
        dalle = self._make_dalle_images()
        html = fmt.generate_html(SAMPLE_DATA, dalle_images=dalle)
        # Should contain <image> tags for icons instead of emoji
        assert "<image" in html
        assert "data:image/png;base64," in html

    def test_sketchnote_without_dalle(self):
        from pipeline.formats.sketchnote import SketchnoteFormat
        fmt = SketchnoteFormat()
        html = fmt.generate_html(SAMPLE_DATA, dalle_images=None)
        # Should fallback to emoji icons
        assert "\U0001f4a1" in html  # lightbulb emoji

    def test_sketchnote_with_background(self):
        from pipeline.formats.sketchnote import SketchnoteFormat
        fmt = SketchnoteFormat()
        dalle = self._make_dalle_images()
        html = fmt.generate_html(SAMPLE_DATA, dalle_images=dalle)
        assert 'opacity="0.08"' in html

    def test_infografia_with_dalle_icons(self):
        from pipeline.formats.infografia import InfografiaFormat
        fmt = InfografiaFormat()
        dalle = self._make_dalle_images()
        html = fmt.generate_html(SAMPLE_DATA, dalle_images=dalle)
        assert "<image" in html
        assert "data:image/png;base64," in html

    def test_infografia_without_dalle_has_numbers(self):
        from pipeline.formats.infografia import InfografiaFormat
        fmt = InfografiaFormat()
        html = fmt.generate_html(SAMPLE_DATA, dalle_images=None)
        assert ">1<" in html
        assert ">2<" in html

    def test_mindmap_with_background(self):
        from pipeline.formats.mindmap_format import MindmapFormat
        fmt = MindmapFormat()
        dalle = self._make_dalle_images()
        html = fmt.generate_html(SAMPLE_DATA, dalle_images=dalle)
        assert 'opacity="0.06"' in html

    def test_mindmap_without_dalle(self):
        from pipeline.formats.mindmap_format import MindmapFormat
        fmt = MindmapFormat()
        html = fmt.generate_html(SAMPLE_DATA, dalle_images=None)
        # Should not have any DALL-E image tags
        assert "dalle" not in html.lower() or "<image" not in html
