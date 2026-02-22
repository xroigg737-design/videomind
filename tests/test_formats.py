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

SAMPLE_CORE_STRUCTURE = {
    "thesis": "Neural networks transform data processing",
    "content_type": "explanatory",
    "nuclear_ideas": [
        {
            "idea": "Architecture defines network capacity",
            "sub_ideas": ["Layers organize neurons", "Depth adds abstraction"],
            "structural_role": "concept",
        },
        {
            "idea": "Training optimizes network weights",
            "sub_ideas": ["Backpropagation computes gradients", "Loss function guides learning"],
            "structural_role": "component",
        },
        {
            "idea": "Applications span many domains",
            "sub_ideas": ["Vision and language tasks", "Healthcare and robotics"],
            "structural_role": "consequence",
        },
    ],
    "memorable_phrase": "Data is the new oil",
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


class TestCollectAllViolations:
    def test_mindmap_valid(self):
        from pipeline.formats.validators import collect_all_violations

        data = {
            "central_node": "ML Topic",
            "branches": [
                {"title": "Branch one", "children": [
                    {"title": "Child A", "children": []},
                    {"title": "Child B", "children": []},
                ]},
                {"title": "Branch two", "children": []},
                {"title": "Branch three", "children": []},
            ],
        }
        assert collect_all_violations(data, "mindmap") == []

    def test_mindmap_too_many_branches(self):
        from pipeline.formats.validators import collect_all_violations

        data = {
            "central_node": "ML",
            "branches": [{"title": f"B{i}", "children": []} for i in range(8)],
        }
        violations = collect_all_violations(data, "mindmap")
        assert any("branches" in v for v in violations)

    def test_infografia_valid(self):
        from pipeline.formats.validators import collect_all_violations

        assert collect_all_violations(SAMPLE_INFOGRAFIA_DATA, "infografia") == []


# ---------------------------------------------------------------------------
# Distiller (Phase 1 & 2)
# ---------------------------------------------------------------------------


class TestValidateDistillation:
    def test_valid_core(self):
        from pipeline.formats.distiller import validate_distillation

        assert validate_distillation(SAMPLE_CORE_STRUCTURE) == []

    def test_too_many_ideas(self):
        from pipeline.formats.distiller import validate_distillation

        bad = dict(SAMPLE_CORE_STRUCTURE)
        bad["nuclear_ideas"] = SAMPLE_CORE_STRUCTURE["nuclear_ideas"] * 3
        errors = validate_distillation(bad)
        assert any("nuclear ideas" in e for e in errors)

    def test_long_thesis(self):
        from pipeline.formats.distiller import validate_distillation

        bad = dict(SAMPLE_CORE_STRUCTURE)
        bad["thesis"] = "This is a very long thesis that has way more than fifteen words in it for sure"
        errors = validate_distillation(bad)
        assert any("thesis" in e for e in errors)


class TestBuildStructuralModel:
    def test_groups_by_role(self):
        from pipeline.formats.distiller import build_structural_model

        model = build_structural_model(SAMPLE_CORE_STRUCTURE)
        assert model["content_type"] == "explanatory"
        assert "concept" in model["structure"]
        assert "component" in model["structure"]
        assert "consequence" in model["structure"]
        assert len(model["structure"]["concept"]) == 1
        assert len(model["structure"]["component"]) == 1

    def test_unassigned_goes_to_emptiest(self):
        from pipeline.formats.distiller import build_structural_model

        core = {
            "thesis": "Test",
            "content_type": "narrative",
            "nuclear_ideas": [
                {"idea": "A", "sub_ideas": ["a1", "a2"], "structural_role": "unknown_role"},
                {"idea": "B", "sub_ideas": ["b1", "b2"], "structural_role": "problem"},
            ],
            "memorable_phrase": "",
        }
        model = build_structural_model(core)
        # "A" had unknown role, should go to emptiest slot (method or result)
        all_ideas = []
        for slot_ideas in model["structure"].values():
            all_ideas.extend(slot_ideas)
        assert len(all_ideas) == 2


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

        assert isinstance(SYSTEM_PROMPT, str)
        assert len(SYSTEM_PROMPT) > 10

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
    @patch("pipeline.formats.distiller.anthropic.Anthropic")
    def test_output_files_named_mindmap(self, mock_distiller_cls, mock_base_cls, tmp_path):
        from pipeline.mindmap import generate_mindmap

        # Phase 1: distiller returns core structure
        distiller_response = MagicMock()
        distiller_response.content = [MagicMock(text=json.dumps(SAMPLE_CORE_STRUCTURE))]
        mock_distiller_client = MagicMock()
        mock_distiller_client.messages.create.return_value = distiller_response
        mock_distiller_cls.return_value = mock_distiller_client

        # Phase 3: transform returns sketchnote data
        transform_response = MagicMock()
        transform_response.content = [MagicMock(text=json.dumps(SAMPLE_SKETCHNOTE_DATA))]
        mock_base_client = MagicMock()
        mock_base_client.messages.create.return_value = transform_response
        mock_base_cls.return_value = mock_base_client

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
