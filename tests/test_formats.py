"""Tests for the multi-format visual generation system (pipeline.formats)."""

import json
import os
import sys
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


# ---------------------------------------------------------------------------
# Sample data fixtures
# ---------------------------------------------------------------------------

SAMPLE_SKETCHNOTE_DATA = {
    "title": "Neural Networks",
    "sections": [
        {
            "id": "s1",
            "heading": "Architecture",
            "icon": "\U0001f3d7\ufe0f",
            "metaphor": "building with LEGO bricks",
            "points": ["Layers organize neurons", "Deep vs shallow networks"],
            "color": "#4A90D9",
        },
        {
            "id": "s2",
            "heading": "Training",
            "icon": "\U0001f3cb\ufe0f",
            "metaphor": "training a muscle",
            "points": ["Backpropagation", "Gradient descent optimization"],
            "color": "#E67E22",
        },
    ],
    "connections": [
        {"from": "s1", "to": "s2", "label": "feeds into"},
    ],
}

SAMPLE_MINDMAP_DATA = {
    "type": "mindmap",
    "central_node": "Machine Learning",
    "branches": [
        {
            "title": "Supervised Learning",
            "children": [
                {"title": "Classification", "children": []},
                {"title": "Regression", "children": []},
            ],
        },
        {
            "title": "Unsupervised Learning",
            "children": [
                {"title": "Clustering", "children": []},
            ],
        },
        {
            "title": "Reinforcement Learning",
            "children": [
                {"title": "Policy Gradient", "children": []},
            ],
        },
        {
            "title": "Feature Engineering",
            "children": [],
        },
        {
            "title": "Model Evaluation",
            "children": [
                {"title": "Cross Validation", "children": []},
            ],
        },
    ],
}

SAMPLE_INFOGRAFIA_DATA = {
    "type": "infografia",
    "headline": "AI Transforms Education",
    "sections": [
        {
            "title": "Problema",
            "icon": "\u26a0\ufe0f",
            "bullets": ["Students lack personalized attention", "One-size-fits-all approach"],
        },
        {
            "title": "M\u00e8tode",
            "icon": "\U0001f9ea",
            "bullets": ["Adaptive algorithms tailor content", "Real-time feedback loops"],
        },
        {
            "title": "Resultat",
            "icon": "\U0001f3af",
            "bullets": ["Improved retention rates", "Higher student engagement"],
        },
    ],
    "closing_phrase": "Every learner deserves a unique path",
}


# ---------------------------------------------------------------------------
# Validators
# ---------------------------------------------------------------------------


class TestCheckWordCount:
    def test_passes_within_limit(self):
        from pipeline.formats.validators import check_word_count

        assert check_word_count("hello world", 5, "test") is None

    def test_warns_over_limit(self):
        from pipeline.formats.validators import check_word_count

        w = check_word_count("one two three four five six", 3, "field")
        assert w is not None
        assert "6 words" in w


class TestCheckListLength:
    def test_passes_within_range(self):
        from pipeline.formats.validators import check_list_length

        assert check_list_length([1, 2, 3], 2, 5, "items") is None

    def test_warns_below_min(self):
        from pipeline.formats.validators import check_list_length

        w = check_list_length([1], 2, 5, "items")
        assert w is not None
        assert "1 items" in w

    def test_warns_above_max(self):
        from pipeline.formats.validators import check_list_length

        w = check_list_length([1, 2, 3, 4, 5, 6], 2, 5, "items")
        assert w is not None
        assert "6 items" in w


class TestCheckExactCount:
    def test_passes_exact(self):
        from pipeline.formats.validators import check_exact_count

        assert check_exact_count([1, 2, 3], 3, "sections") is None

    def test_warns_wrong_count(self):
        from pipeline.formats.validators import check_exact_count

        w = check_exact_count([1, 2], 3, "sections")
        assert w is not None
        assert "2 items" in w


class TestCheckMaxDepth:
    def test_passes_within_depth(self):
        from pipeline.formats.validators import check_max_depth

        tree = {"title": "root", "children": [{"title": "leaf", "children": []}]}
        assert check_max_depth(tree, 3) is None

    def test_warns_exceeds_depth(self):
        from pipeline.formats.validators import check_max_depth

        deep = {
            "title": "a",
            "children": [
                {
                    "title": "b",
                    "children": [
                        {
                            "title": "c",
                            "children": [{"title": "d", "children": []}],
                        }
                    ],
                }
            ],
        }
        w = check_max_depth(deep, 3)
        assert w is not None
        assert "depth" in w.lower()


# ---------------------------------------------------------------------------
# Dispatcher
# ---------------------------------------------------------------------------


class TestDispatcher:
    def test_get_format_returns_correct_type(self):
        from pipeline.formats import get_format
        from pipeline.formats.sketchnote import SketchnoteFormat
        from pipeline.formats.mindmap_format import MindmapFormat
        from pipeline.formats.infografia import InfografiaFormat

        assert isinstance(get_format("sketchnote"), SketchnoteFormat)
        assert isinstance(get_format("mindmap"), MindmapFormat)
        assert isinstance(get_format("infografia"), InfografiaFormat)

    def test_get_format_raises_on_unknown(self):
        from pipeline.formats import get_format

        with pytest.raises(ValueError, match="Unknown visual format"):
            get_format("nonexistent")

    @patch("pipeline.formats.sketchnote.SketchnoteFormat.generate")
    def test_generate_visual_format_delegates_sketchnote(self, mock_gen):
        from pipeline.formats import generate_visual_format

        mock_gen.return_value = {"data": {}}
        generate_visual_format("transcript", "/tmp", format_type="sketchnote")
        mock_gen.assert_called_once()

    @patch("pipeline.formats.mindmap_format.MindmapFormat.generate")
    def test_generate_visual_format_delegates_mindmap(self, mock_gen):
        from pipeline.formats import generate_visual_format

        mock_gen.return_value = {"data": {}}
        generate_visual_format("transcript", "/tmp", format_type="mindmap")
        mock_gen.assert_called_once()

    @patch("pipeline.formats.infografia.InfografiaFormat.generate")
    def test_generate_visual_format_delegates_infografia(self, mock_gen):
        from pipeline.formats import generate_visual_format

        mock_gen.return_value = {"data": {}}
        generate_visual_format("transcript", "/tmp", format_type="infografia")
        mock_gen.assert_called_once()


# ---------------------------------------------------------------------------
# Sketchnote format
# ---------------------------------------------------------------------------


class TestSketchnoteMarkdown:
    def test_contains_title(self):
        from pipeline.formats.sketchnote import SketchnoteFormat

        fmt = SketchnoteFormat()
        md = fmt.generate_markdown(SAMPLE_SKETCHNOTE_DATA)
        assert md.startswith("# Neural Networks\n")

    def test_contains_section_headings(self):
        from pipeline.formats.sketchnote import SketchnoteFormat

        fmt = SketchnoteFormat()
        md = fmt.generate_markdown(SAMPLE_SKETCHNOTE_DATA)
        assert "Architecture" in md
        assert "Training" in md

    def test_contains_bullets(self):
        from pipeline.formats.sketchnote import SketchnoteFormat

        fmt = SketchnoteFormat()
        md = fmt.generate_markdown(SAMPLE_SKETCHNOTE_DATA)
        assert "- Layers organize neurons" in md


class TestSketchnoteHtml:
    def test_contains_svg(self):
        from pipeline.formats.sketchnote import SketchnoteFormat

        fmt = SketchnoteFormat()
        html = fmt.generate_html(SAMPLE_SKETCHNOTE_DATA)
        assert "<svg" in html
        assert "</svg>" in html

    def test_contains_title(self):
        from pipeline.formats.sketchnote import SketchnoteFormat

        fmt = SketchnoteFormat()
        html = fmt.generate_html(SAMPLE_SKETCHNOTE_DATA)
        assert "Neural Networks" in html

    def test_contains_sketchy_filter(self):
        from pipeline.formats.sketchnote import SketchnoteFormat

        fmt = SketchnoteFormat()
        html = fmt.generate_html(SAMPLE_SKETCHNOTE_DATA)
        assert "feTurbulence" in html

    def test_contains_connection(self):
        from pipeline.formats.sketchnote import SketchnoteFormat

        fmt = SketchnoteFormat()
        html = fmt.generate_html(SAMPLE_SKETCHNOTE_DATA)
        assert "feeds into" in html


class TestSketchnoteValidation:
    def test_valid_data_no_warnings(self):
        from pipeline.formats.sketchnote import SketchnoteFormat

        fmt = SketchnoteFormat()
        data = {
            "title": "Test",
            "sections": [
                {"id": f"s{i}", "heading": "Head", "icon": "x", "points": ["Short point"], "color": "#000"}
                for i in range(5)
            ],
            "connections": [],
        }
        assert fmt.validate(data) == []

    def test_warns_too_few_sections(self):
        from pipeline.formats.sketchnote import SketchnoteFormat

        fmt = SketchnoteFormat()
        data = {
            "title": "Test",
            "sections": [
                {"id": "s1", "heading": "H", "icon": "x", "points": ["P"], "color": "#000"}
            ],
            "connections": [],
        }
        warnings = fmt.validate(data)
        assert any("sections" in w for w in warnings)


# ---------------------------------------------------------------------------
# Mindmap format
# ---------------------------------------------------------------------------


class TestMindmapMarkdown:
    def test_contains_central_node(self):
        from pipeline.formats.mindmap_format import MindmapFormat

        fmt = MindmapFormat()
        md = fmt.generate_markdown(SAMPLE_MINDMAP_DATA)
        assert "# Machine Learning" in md

    def test_contains_branches(self):
        from pipeline.formats.mindmap_format import MindmapFormat

        fmt = MindmapFormat()
        md = fmt.generate_markdown(SAMPLE_MINDMAP_DATA)
        assert "## Supervised Learning" in md
        assert "## Unsupervised Learning" in md

    def test_contains_children(self):
        from pipeline.formats.mindmap_format import MindmapFormat

        fmt = MindmapFormat()
        md = fmt.generate_markdown(SAMPLE_MINDMAP_DATA)
        assert "- Classification" in md
        assert "- Regression" in md


class TestMindmapHtml:
    def test_contains_svg(self):
        from pipeline.formats.mindmap_format import MindmapFormat

        fmt = MindmapFormat()
        html = fmt.generate_html(SAMPLE_MINDMAP_DATA)
        assert "<svg" in html
        assert "</svg>" in html

    def test_contains_central_node(self):
        from pipeline.formats.mindmap_format import MindmapFormat

        fmt = MindmapFormat()
        html = fmt.generate_html(SAMPLE_MINDMAP_DATA)
        assert "Machine Learning" in html

    def test_contains_branches(self):
        from pipeline.formats.mindmap_format import MindmapFormat

        fmt = MindmapFormat()
        html = fmt.generate_html(SAMPLE_MINDMAP_DATA)
        assert "Supervised Learning" in html

    def test_contains_sketchy_filter(self):
        from pipeline.formats.mindmap_format import MindmapFormat

        fmt = MindmapFormat()
        html = fmt.generate_html(SAMPLE_MINDMAP_DATA)
        assert "feTurbulence" in html
        assert "Caveat" in html


class TestMindmapValidation:
    def test_valid_data_no_warnings(self):
        from pipeline.formats.mindmap_format import MindmapFormat

        fmt = MindmapFormat()
        assert fmt.validate(SAMPLE_MINDMAP_DATA) == []

    def test_warns_too_few_branches(self):
        from pipeline.formats.mindmap_format import MindmapFormat

        fmt = MindmapFormat()
        data = {
            "central_node": "Test",
            "branches": [{"title": "Only one", "children": []}],
        }
        warnings = fmt.validate(data)
        assert any("branches" in w for w in warnings)

    def test_warns_deep_tree(self):
        from pipeline.formats.mindmap_format import MindmapFormat

        fmt = MindmapFormat()
        data = {
            "central_node": "Test",
            "branches": [
                {
                    "title": "L1",
                    "children": [
                        {
                            "title": "L2",
                            "children": [
                                {
                                    "title": "L3",
                                    "children": [{"title": "L4", "children": []}],
                                }
                            ],
                        }
                    ],
                },
                {"title": "B2", "children": []},
                {"title": "B3", "children": []},
                {"title": "B4", "children": []},
                {"title": "B5", "children": []},
            ],
        }
        warnings = fmt.validate(data)
        assert any("depth" in w.lower() for w in warnings)


# ---------------------------------------------------------------------------
# Infografia format
# ---------------------------------------------------------------------------


class TestInfografiaMarkdown:
    def test_contains_headline(self):
        from pipeline.formats.infografia import InfografiaFormat

        fmt = InfografiaFormat()
        md = fmt.generate_markdown(SAMPLE_INFOGRAFIA_DATA)
        assert "# AI Transforms Education" in md

    def test_contains_sections(self):
        from pipeline.formats.infografia import InfografiaFormat

        fmt = InfografiaFormat()
        md = fmt.generate_markdown(SAMPLE_INFOGRAFIA_DATA)
        assert "Problema" in md
        assert "M\u00e8tode" in md
        assert "Resultat" in md

    def test_contains_closing_phrase(self):
        from pipeline.formats.infografia import InfografiaFormat

        fmt = InfografiaFormat()
        md = fmt.generate_markdown(SAMPLE_INFOGRAFIA_DATA)
        assert "Every learner deserves a unique path" in md

    def test_contains_bullets(self):
        from pipeline.formats.infografia import InfografiaFormat

        fmt = InfografiaFormat()
        md = fmt.generate_markdown(SAMPLE_INFOGRAFIA_DATA)
        assert "- Students lack personalized attention" in md


class TestInfografiaHtml:
    def test_contains_svg(self):
        from pipeline.formats.infografia import InfografiaFormat

        fmt = InfografiaFormat()
        html = fmt.generate_html(SAMPLE_INFOGRAFIA_DATA)
        assert "<svg" in html
        assert "</svg>" in html

    def test_contains_headline(self):
        from pipeline.formats.infografia import InfografiaFormat

        fmt = InfografiaFormat()
        html = fmt.generate_html(SAMPLE_INFOGRAFIA_DATA)
        assert "AI Transforms Education" in html

    def test_contains_panel_colors(self):
        from pipeline.formats.infografia import InfografiaFormat

        fmt = InfografiaFormat()
        html = fmt.generate_html(SAMPLE_INFOGRAFIA_DATA)
        assert "#E74C3C" in html  # Problema
        assert "#3498DB" in html  # Metode
        assert "#2ECC71" in html  # Resultat

    def test_contains_closing_phrase(self):
        from pipeline.formats.infografia import InfografiaFormat

        fmt = InfografiaFormat()
        html = fmt.generate_html(SAMPLE_INFOGRAFIA_DATA)
        assert "Every learner deserves a unique path" in html

    def test_contains_sketchy_filter(self):
        from pipeline.formats.infografia import InfografiaFormat

        fmt = InfografiaFormat()
        html = fmt.generate_html(SAMPLE_INFOGRAFIA_DATA)
        assert "feTurbulence" in html


class TestInfografiaValidation:
    def test_valid_data_no_warnings(self):
        from pipeline.formats.infografia import InfografiaFormat

        fmt = InfografiaFormat()
        assert fmt.validate(SAMPLE_INFOGRAFIA_DATA) == []

    def test_warns_wrong_section_count(self):
        from pipeline.formats.infografia import InfografiaFormat

        fmt = InfografiaFormat()
        data = {
            "headline": "Test",
            "sections": [
                {"title": "Problema", "icon": "x", "bullets": ["a"]},
                {"title": "M\u00e8tode", "icon": "x", "bullets": ["a"]},
            ],
            "closing_phrase": "Short",
        }
        warnings = fmt.validate(data)
        assert any("sections" in w for w in warnings)

    def test_warns_wrong_titles(self):
        from pipeline.formats.infografia import InfografiaFormat

        fmt = InfografiaFormat()
        data = {
            "headline": "Test",
            "sections": [
                {"title": "Problema", "icon": "x", "bullets": ["a"]},
                {"title": "Approach", "icon": "x", "bullets": ["a"]},
                {"title": "Resultat", "icon": "x", "bullets": ["a"]},
            ],
            "closing_phrase": "Short",
        }
        warnings = fmt.validate(data)
        assert any("titles" in w.lower() for w in warnings)

    def test_warns_long_headline(self):
        from pipeline.formats.infografia import InfografiaFormat

        fmt = InfografiaFormat()
        data = {
            "headline": "This is a very long headline that exceeds eight words limit",
            "sections": [
                {"title": "Problema", "icon": "x", "bullets": ["a"]},
                {"title": "M\u00e8tode", "icon": "x", "bullets": ["a"]},
                {"title": "Resultat", "icon": "x", "bullets": ["a"]},
            ],
            "closing_phrase": "Short",
        }
        warnings = fmt.validate(data)
        assert any("headline" in w for w in warnings)


# ---------------------------------------------------------------------------
# Backward compatibility (pipeline.mindmap wrapper)
# ---------------------------------------------------------------------------


class TestBackwardCompat:
    def test_generate_mindmap_still_importable(self):
        from pipeline.mindmap import generate_mindmap

        assert callable(generate_mindmap)

    def test_call_claude_still_importable(self):
        from pipeline.mindmap import _call_claude

        assert callable(_call_claude)

    def test_max_transcript_length_importable(self):
        from pipeline.mindmap import MAX_TRANSCRIPT_LENGTH

        assert MAX_TRANSCRIPT_LENGTH == 100_000

    def test_system_prompt_importable(self):
        from pipeline.mindmap import SYSTEM_PROMPT

        assert "sketchnote" in SYSTEM_PROMPT.lower()

    @patch("pipeline.formats.base.anthropic.Anthropic")
    def test_call_claude_works(self, mock_cls):
        from pipeline.mindmap import _call_claude

        mock_response = MagicMock()
        mock_response.content = [MagicMock(text=json.dumps(SAMPLE_SKETCHNOTE_DATA))]
        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_response
        mock_cls.return_value = mock_client

        result = _call_claude("some transcript")
        assert result["title"] == "Neural Networks"

    @patch("pipeline.formats.base.anthropic.Anthropic")
    def test_output_files_named_mindmap(self, mock_cls, tmp_path):
        from pipeline.mindmap import generate_mindmap

        mock_response = MagicMock()
        mock_response.content = [MagicMock(text=json.dumps(SAMPLE_SKETCHNOTE_DATA))]
        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_response
        mock_cls.return_value = mock_client

        result = generate_mindmap("test transcript", str(tmp_path), formats="all")
        assert result["json_path"].endswith("mindmap.json")
        assert result["md_path"].endswith("mindmap.md")
        assert result["html_path"].endswith("mindmap.html")


# ---------------------------------------------------------------------------
# Base helpers
# ---------------------------------------------------------------------------


class TestExtractJson:
    def test_plain_json(self):
        from pipeline.formats.base import _extract_json_from_response

        data = _extract_json_from_response('{"key": "value"}')
        assert data == {"key": "value"}

    def test_code_block_json(self):
        from pipeline.formats.base import _extract_json_from_response

        data = _extract_json_from_response('```json\n{"key": "value"}\n```')
        assert data == {"key": "value"}

    def test_code_block_no_language(self):
        from pipeline.formats.base import _extract_json_from_response

        data = _extract_json_from_response('```\n{"key": "value"}\n```')
        assert data == {"key": "value"}
