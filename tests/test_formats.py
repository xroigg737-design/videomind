"""Tests for the multi-format visual generation system (pipeline.formats).

Updated for the 3-layer architecture:
  Layer 1 — Content Engine (unified JSON)
  Layer 2 — Content Reducer
  Layer 3 — Layout Engine (format-specific rendering)
"""

import json
import os
import sys
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


# ---------------------------------------------------------------------------
# Sample data fixtures — NEW unified JSON schema
# ---------------------------------------------------------------------------

SAMPLE_UNIFIED_DATA = {
    "title": "Neural Networks",
    "central_idea": "Deep learning transforms AI",
    "content_type": "conceptual",
    "sections": [
        {
            "label": "Architecture",
            "bullets": ["Layer organization", "Deep networks"],
            "example": "Convolutional layers for images",
        },
        {
            "label": "Training",
            "bullets": ["Backpropagation", "Gradient descent"],
            "example": "Loss minimization loop",
        },
        {
            "label": "Data Flow",
            "bullets": ["Forward pass", "Loss computation"],
            "example": "Batch processing pipeline",
        },
        {
            "label": "Deployment",
            "bullets": ["Scale models", "Monitor drift"],
            "example": "Cloud inference endpoints",
        },
    ],
    "practice_plan": {
        "daily_5min": ["Review metrics", "Read paper", "Code exercise"],
        "weekly": ["Train model"],
    },
    "cta_removed": "",
}

# Legacy fixtures kept for backward-compat validator tests
SAMPLE_LEGACY_SKETCHNOTE = {
    "title": "NEURAL NETS",
    "sections": [
        {"id": "s1", "heading": "ARCHITECTURE", "icon": "\U0001f3d7\ufe0f",
         "points": ["Organize neurons", "Deep networks"], "color": "#4A90D9"},
        {"id": "s2", "heading": "TRAINING", "icon": "\U0001f3cb\ufe0f",
         "points": ["Backpropagation", "Gradient descent"], "color": "#E67E22"},
        {"id": "s3", "heading": "DATA FLOW", "icon": "\U0001f4ca",
         "points": ["Forward pass", "Loss computation"], "color": "#2ECC71"},
        {"id": "s4", "heading": "DEPLOY", "icon": "\U0001f680",
         "points": ["Scale models", "Monitor drift"], "color": "#9B59B6"},
    ],
    "connections": [{"from": "s1", "to": "s2", "label": "feeds"}],
}

SAMPLE_LEGACY_MINDMAP = {
    "type": "mindmap",
    "central_node": "Machine Learning",
    "branches": [
        {"title": "Supervised Learning", "children": [
            {"title": "Classification", "children": []},
            {"title": "Regression", "children": []},
        ]},
        {"title": "Unsupervised Learning", "children": [
            {"title": "Clustering", "children": []},
        ]},
        {"title": "Reinforcement Learning", "children": [
            {"title": "Policy Gradient", "children": []},
        ]},
        {"title": "Feature Engineering", "children": []},
        {"title": "Model Evaluation", "children": [
            {"title": "Cross Validation", "children": []},
        ]},
    ],
}

SAMPLE_LEGACY_INFOGRAFIA = {
    "type": "infografia",
    "headline": "AI Transforms Education",
    "sections": [
        {"title": "Problema", "icon": "\u26a0\ufe0f",
         "what": "No personalization", "why": "Students fall behind", "impact": "High dropout rates"},
        {"title": "M\u00e8tode", "icon": "\U0001f9ea",
         "what": "Adaptive algorithms", "why": "Real-time feedback", "impact": "Tailored learning paths"},
        {"title": "Resultat", "icon": "\U0001f3af",
         "what": "Better retention", "why": "Engaged students", "impact": "Higher completion rates"},
    ],
    "closing_phrase": "Every learner unique",
}

SAMPLE_CORE_STRUCTURE = {
    "thesis": "Neural network revolution",
    "content_type": "explanatory",
    "nuclear_ideas": [
        {"idea": "Architecture design", "sub_ideas": ["Layer organization", "Depth abstraction"],
         "structural_role": "concept"},
        {"idea": "Training optimization", "sub_ideas": ["Backpropagation gradients", "Loss-guided learning"],
         "structural_role": "component"},
        {"idea": "Cross-domain applications", "sub_ideas": ["Vision language", "Healthcare robotics"],
         "structural_role": "consequence"},
    ],
    "memorable_phrase": "Data fuels intelligence",
}


# ---------------------------------------------------------------------------
# Content Engine (Layer 1)
# ---------------------------------------------------------------------------


class TestContentValidation:
    def test_valid_unified_data(self):
        from pipeline.formats.content_engine import validate_content

        assert validate_content(SAMPLE_UNIFIED_DATA) == []

    def test_too_many_sections(self):
        from pipeline.formats.content_engine import validate_content

        bad = dict(SAMPLE_UNIFIED_DATA)
        bad["sections"] = SAMPLE_UNIFIED_DATA["sections"] * 2  # 8 sections
        violations = validate_content(bad)
        assert any("sections" in v for v in violations)

    def test_title_too_long(self):
        from pipeline.formats.content_engine import validate_content

        bad = dict(SAMPLE_UNIFIED_DATA)
        bad["title"] = "This is a very very very very long title"
        violations = validate_content(bad)
        assert any("title" in v for v in violations)

    def test_bullet_too_long(self):
        from pipeline.formats.content_engine import validate_content

        bad = dict(SAMPLE_UNIFIED_DATA)
        bad["sections"] = [{
            "label": "Test",
            "bullets": ["This bullet is way too long for sure"],
            "example": "",
        }]
        violations = validate_content(bad)
        assert any("bullet" in v for v in violations)

    def test_invalid_content_type(self):
        from pipeline.formats.content_engine import validate_content

        bad = dict(SAMPLE_UNIFIED_DATA)
        bad["content_type"] = "narrative"  # old type, not in new schema
        violations = validate_content(bad)
        assert any("content_type" in v for v in violations)


# ---------------------------------------------------------------------------
# Content Reducer (Layer 2)
# ---------------------------------------------------------------------------


class TestContentReducer:
    def test_reduce_phrase_within_limit(self):
        from pipeline.formats.content_reducer import reduce_phrase

        assert reduce_phrase("Short phrase", 4) == "Short phrase"

    def test_reduce_phrase_strips_filler(self):
        from pipeline.formats.content_reducer import reduce_phrase

        result = reduce_phrase("The very important daily task", 4)
        assert len(result.split()) <= 4

    def test_reduce_content_enforces_limits(self):
        from pipeline.formats.content_reducer import reduce_content, count_visible_words

        reduced = reduce_content(SAMPLE_UNIFIED_DATA)
        # All labels should be <= 4 words
        for sec in reduced["sections"]:
            assert len(sec["label"].split()) <= 4
        # All bullets should be <= 4 words
        for sec in reduced["sections"]:
            for b in sec["bullets"]:
                assert len(b.split()) <= 4
        # Max 4 sections
        assert len(reduced["sections"]) <= 4

    def test_count_visible_words(self):
        from pipeline.formats.content_reducer import count_visible_words

        data = {
            "title": "Two Words",
            "sections": [
                {"label": "One", "bullets": ["Two words"], "example": "Three words here"},
            ],
        }
        assert count_visible_words(data) == 8  # 2 + 1 + 2 + 3

    def test_force_reduce_removes_examples_first(self):
        from pipeline.formats.content_reducer import force_reduce_to_word_limit, count_visible_words

        result = force_reduce_to_word_limit(SAMPLE_UNIFIED_DATA, 40)
        assert count_visible_words(result) <= 40


# ---------------------------------------------------------------------------
# Quality Check
# ---------------------------------------------------------------------------


class TestQualityCheck:
    def test_passes_clean_data(self):
        from pipeline.formats.quality_check import check_quality

        clean = {
            "title": "Short Title",
            "sections": [
                {"label": "One", "bullets": ["Word one", "Word two"], "example": ""},
                {"label": "Two", "bullets": ["Word three"], "example": ""},
            ],
        }
        assert check_quality(clean) == []

    def test_fails_too_many_words(self):
        from pipeline.formats.quality_check import check_quality

        # Create verbose data that exceeds 40 words
        verbose = {
            "title": "Comprehensive Neural Network Guide",
            "sections": [
                {"label": "Architecture Design", "bullets": [
                    "Layer organization methods", "Deep network patterns", "Activation function types",
                ], "example": "Convolutional layers process images effectively"},
                {"label": "Training Optimization", "bullets": [
                    "Backpropagation gradient descent", "Loss function minimization", "Learning rate tuning",
                ], "example": "Stochastic gradient descent works well"},
                {"label": "Data Flow Process", "bullets": [
                    "Forward pass computation", "Loss function evaluation", "Batch processing pipeline",
                ], "example": "Mini batch gradient processing approach"},
                {"label": "Deployment Strategy", "bullets": [
                    "Scale production models", "Monitor model drift", "Continuous model retraining",
                ], "example": "Cloud inference endpoint deployment strategy"},
            ],
        }
        issues = check_quality(verbose)
        assert any("visible words" in i for i in issues)

    def test_ensure_quality_auto_reduces(self):
        from pipeline.formats.quality_check import ensure_quality
        from pipeline.formats.content_reducer import count_visible_words

        result = ensure_quality(SAMPLE_UNIFIED_DATA)
        assert count_visible_words(result) <= 40


# ---------------------------------------------------------------------------
# Validators (supports both unified and legacy schemas)
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
            "children": [{"title": "b", "children": [
                {"title": "c", "children": [{"title": "d", "children": []}]}
            ]}],
        }
        w = check_max_depth(deep, 3)
        assert w is not None
        assert "depth" in w.lower()


class TestCollectAllViolations:
    def test_unified_valid(self):
        from pipeline.formats.validators import collect_all_violations

        assert collect_all_violations(SAMPLE_UNIFIED_DATA, "infografia") == []

    def test_unified_too_many_sections(self):
        from pipeline.formats.validators import collect_all_violations

        bad = dict(SAMPLE_UNIFIED_DATA)
        bad["sections"] = SAMPLE_UNIFIED_DATA["sections"] * 2
        violations = collect_all_violations(bad, "infografia")
        assert any("sections" in v for v in violations)

    def test_legacy_mindmap_valid(self):
        from pipeline.formats.validators import collect_all_violations

        assert collect_all_violations(SAMPLE_LEGACY_MINDMAP, "mindmap") == []

    def test_legacy_mindmap_too_many_branches(self):
        from pipeline.formats.validators import collect_all_violations

        data = {
            "central_node": "ML",
            "branches": [{"title": f"B{i}", "children": []} for i in range(8)],
        }
        violations = collect_all_violations(data, "mindmap")
        assert any("branches" in v for v in violations)

    def test_legacy_infografia_valid(self):
        from pipeline.formats.validators import collect_all_violations

        assert collect_all_violations(SAMPLE_LEGACY_INFOGRAFIA, "infografia") == []


# ---------------------------------------------------------------------------
# Heuristic format detection
# ---------------------------------------------------------------------------


class TestHeuristicDetection:
    def test_procedural_to_infografia(self):
        from pipeline.formats import detect_best_format

        assert detect_best_format("procedural") == "infografia"

    def test_conceptual_to_mindmap(self):
        from pipeline.formats import detect_best_format

        assert detect_best_format("conceptual") == "mindmap"

    def test_pedagogical_to_sketchnote(self):
        from pipeline.formats import detect_best_format

        assert detect_best_format("pedagogical") == "sketchnote"

    def test_unknown_defaults_to_sketchnote(self):
        from pipeline.formats import detect_best_format

        assert detect_best_format("unknown") == "sketchnote"


# ---------------------------------------------------------------------------
# Distiller (Phase 1 & 2 — kept for backward compat)
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
# Sketchnote format (unified JSON)
# ---------------------------------------------------------------------------


class TestSketchnoteMarkdown:
    def test_contains_title(self):
        from pipeline.formats.sketchnote import SketchnoteFormat

        fmt = SketchnoteFormat()
        md = fmt.generate_markdown(SAMPLE_UNIFIED_DATA)
        assert md.startswith("# Neural Networks\n")

    def test_contains_section_labels(self):
        from pipeline.formats.sketchnote import SketchnoteFormat

        fmt = SketchnoteFormat()
        md = fmt.generate_markdown(SAMPLE_UNIFIED_DATA)
        assert "Architecture" in md
        assert "Training" in md

    def test_contains_bullets(self):
        from pipeline.formats.sketchnote import SketchnoteFormat

        fmt = SketchnoteFormat()
        md = fmt.generate_markdown(SAMPLE_UNIFIED_DATA)
        assert "- Layer organization" in md

    def test_contains_practice_plan(self):
        from pipeline.formats.sketchnote import SketchnoteFormat

        fmt = SketchnoteFormat()
        md = fmt.generate_markdown(SAMPLE_UNIFIED_DATA)
        assert "Practice Plan" in md
        assert "Review metrics" in md


class TestSketchnoteHtml:
    def test_contains_svg(self):
        from pipeline.formats.sketchnote import SketchnoteFormat

        fmt = SketchnoteFormat()
        html = fmt.generate_html(SAMPLE_UNIFIED_DATA)
        assert "<svg" in html
        assert "</svg>" in html

    def test_contains_title(self):
        from pipeline.formats.sketchnote import SketchnoteFormat

        fmt = SketchnoteFormat()
        html = fmt.generate_html(SAMPLE_UNIFIED_DATA)
        assert "Neural Networks" in html

    def test_contains_sketchy_filter(self):
        from pipeline.formats.sketchnote import SketchnoteFormat

        fmt = SketchnoteFormat()
        html = fmt.generate_html(SAMPLE_UNIFIED_DATA)
        assert "feTurbulence" in html

    def test_contains_design_tokens(self):
        from pipeline.formats.sketchnote import SketchnoteFormat

        fmt = SketchnoteFormat()
        html = fmt.generate_html(SAMPLE_UNIFIED_DATA)
        assert "#2D5BFF" in html  # Primary color
        assert "Caveat" in html  # Sketch font

    def test_four_quadrants(self):
        from pipeline.formats.sketchnote import SketchnoteFormat

        fmt = SketchnoteFormat()
        html = fmt.generate_html(SAMPLE_UNIFIED_DATA)
        # Should contain all 4 section labels
        assert "Architecture" in html
        assert "Training" in html
        assert "Data Flow" in html
        assert "Deployment" in html


# ---------------------------------------------------------------------------
# Mindmap format (unified JSON)
# ---------------------------------------------------------------------------


class TestMindmapMarkdown:
    def test_contains_title(self):
        from pipeline.formats.mindmap_format import MindmapFormat

        fmt = MindmapFormat()
        md = fmt.generate_markdown(SAMPLE_UNIFIED_DATA)
        assert "# Neural Networks" in md

    def test_contains_sections_as_branches(self):
        from pipeline.formats.mindmap_format import MindmapFormat

        fmt = MindmapFormat()
        md = fmt.generate_markdown(SAMPLE_UNIFIED_DATA)
        assert "## Architecture" in md
        assert "## Training" in md

    def test_contains_bullets(self):
        from pipeline.formats.mindmap_format import MindmapFormat

        fmt = MindmapFormat()
        md = fmt.generate_markdown(SAMPLE_UNIFIED_DATA)
        assert "- Layer organization" in md
        assert "- Backpropagation" in md


class TestMindmapHtml:
    def test_contains_svg(self):
        from pipeline.formats.mindmap_format import MindmapFormat

        fmt = MindmapFormat()
        html = fmt.generate_html(SAMPLE_UNIFIED_DATA)
        assert "<svg" in html
        assert "</svg>" in html

    def test_contains_title_in_central_node(self):
        from pipeline.formats.mindmap_format import MindmapFormat

        fmt = MindmapFormat()
        html = fmt.generate_html(SAMPLE_UNIFIED_DATA)
        assert "Neural Networks" in html

    def test_contains_branch_labels(self):
        from pipeline.formats.mindmap_format import MindmapFormat

        fmt = MindmapFormat()
        html = fmt.generate_html(SAMPLE_UNIFIED_DATA)
        assert "Architecture" in html

    def test_contains_design_tokens(self):
        from pipeline.formats.mindmap_format import MindmapFormat

        fmt = MindmapFormat()
        html = fmt.generate_html(SAMPLE_UNIFIED_DATA)
        assert "Inter" in html
        assert "#FFFFFF" in html
        assert "#2D5BFF" in html  # Primary color


# ---------------------------------------------------------------------------
# Infografia format (unified JSON)
# ---------------------------------------------------------------------------


class TestInfografiaMarkdown:
    def test_contains_title(self):
        from pipeline.formats.infografia import InfografiaFormat

        fmt = InfografiaFormat()
        md = fmt.generate_markdown(SAMPLE_UNIFIED_DATA)
        assert "# Neural Networks" in md

    def test_contains_sections(self):
        from pipeline.formats.infografia import InfografiaFormat

        fmt = InfografiaFormat()
        md = fmt.generate_markdown(SAMPLE_UNIFIED_DATA)
        assert "Architecture" in md
        assert "Training" in md

    def test_contains_bullets(self):
        from pipeline.formats.infografia import InfografiaFormat

        fmt = InfografiaFormat()
        md = fmt.generate_markdown(SAMPLE_UNIFIED_DATA)
        assert "- Layer organization" in md

    def test_no_what_why_impact(self):
        from pipeline.formats.infografia import InfografiaFormat

        fmt = InfografiaFormat()
        md = fmt.generate_markdown(SAMPLE_UNIFIED_DATA)
        # The old WHAT/WHY/IMPACT pattern should be gone
        assert "**What:**" not in md
        assert "**Why:**" not in md
        assert "**Impact:**" not in md


class TestInfografiaHtml:
    def test_contains_svg(self):
        from pipeline.formats.infografia import InfografiaFormat

        fmt = InfografiaFormat()
        html = fmt.generate_html(SAMPLE_UNIFIED_DATA)
        assert "<svg" in html
        assert "</svg>" in html

    def test_contains_title(self):
        from pipeline.formats.infografia import InfografiaFormat

        fmt = InfografiaFormat()
        html = fmt.generate_html(SAMPLE_UNIFIED_DATA)
        assert "Neural Networks" in html

    def test_contains_design_tokens(self):
        from pipeline.formats.infografia import InfografiaFormat

        fmt = InfografiaFormat()
        html = fmt.generate_html(SAMPLE_UNIFIED_DATA)
        assert "#2D5BFF" in html  # Primary
        assert "Inter" in html  # Font
        assert "#FFFFFF" in html  # Background

    def test_no_what_why_impact_labels(self):
        from pipeline.formats.infografia import InfografiaFormat

        fmt = InfografiaFormat()
        html = fmt.generate_html(SAMPLE_UNIFIED_DATA)
        # The old WHAT/WHY/IMPACT pattern should be gone
        assert "WHAT" not in html
        assert "WHY" not in html
        assert "IMPACT" not in html

    def test_contains_section_numbers(self):
        from pipeline.formats.infografia import InfografiaFormat

        fmt = InfografiaFormat()
        html = fmt.generate_html(SAMPLE_UNIFIED_DATA)
        # Should have numbered sections (1, 2, 3, 4)
        assert ">1<" in html
        assert ">2<" in html


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

    @patch("pipeline.formats.content_engine.anthropic.Anthropic")
    def test_output_files_named_mindmap(self, mock_engine_cls, tmp_path):
        from pipeline.mindmap import generate_mindmap

        # Mock the content engine LLM call to return unified JSON
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text=json.dumps(SAMPLE_UNIFIED_DATA))]
        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_response
        mock_engine_cls.return_value = mock_client

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


class TestLightenColor:
    def test_lightens_toward_white(self):
        from pipeline.formats.base import lighten_color

        result = lighten_color("#000000", 0.5)
        assert result == "#7f7f7f"

    def test_full_lighten_is_white(self):
        from pipeline.formats.base import lighten_color

        result = lighten_color("#000000", 1.0)
        assert result == "#ffffff"

    def test_zero_lighten_unchanged(self):
        from pipeline.formats.base import lighten_color

        result = lighten_color("#2D5BFF", 0.0)
        assert result == "#2d5bff"
