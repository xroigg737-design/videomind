"""Tests for the VideoMind pipeline modules."""

import json
import os
import sys
from unittest.mock import MagicMock, patch

import pytest

# Ensure project root is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


# ---------------------------------------------------------------------------
# config.py
# ---------------------------------------------------------------------------


class TestValidateConfig:
    def test_returns_true_when_api_key_set(self, monkeypatch):
        monkeypatch.setattr("config.ANTHROPIC_API_KEY", "sk-test-key")
        from config import validate_config

        assert validate_config() is True

    def test_returns_false_when_api_key_empty(self, monkeypatch):
        monkeypatch.setattr("config.ANTHROPIC_API_KEY", "")
        from config import validate_config

        assert validate_config() is False


# ---------------------------------------------------------------------------
# pipeline/downloader.py – sanitize_filename
# ---------------------------------------------------------------------------


class TestSanitizeFilename:
    def test_removes_unsafe_characters(self):
        from pipeline.downloader import sanitize_filename

        assert sanitize_filename('Hello: "World" <test>') == "Hello World test"

    def test_strips_trailing_dots_and_spaces(self):
        from pipeline.downloader import sanitize_filename

        assert sanitize_filename("title...") == "title"

    def test_returns_untitled_for_empty_string(self):
        from pipeline.downloader import sanitize_filename

        assert sanitize_filename("") == "untitled"

    def test_truncates_long_names(self):
        from pipeline.downloader import sanitize_filename

        long_name = "a" * 300
        result = sanitize_filename(long_name)
        assert len(result) == 200

    def test_preserves_normal_characters(self):
        from pipeline.downloader import sanitize_filename

        assert sanitize_filename("My Great Video 2024") == "My Great Video 2024"


# ---------------------------------------------------------------------------
# pipeline/downloader.py – _ProgressHook
# ---------------------------------------------------------------------------


class TestProgressHook:
    def test_creates_bar_on_downloading(self):
        from pipeline.downloader import _ProgressHook

        hook = _ProgressHook()
        hook({"status": "downloading", "total_bytes": 1000, "downloaded_bytes": 500})
        assert hook.bar is not None
        hook.bar.close()

    def test_closes_bar_on_finished(self):
        from pipeline.downloader import _ProgressHook

        hook = _ProgressHook()
        hook({"status": "downloading", "total_bytes": 1000, "downloaded_bytes": 500})
        hook({"status": "finished"})
        assert hook.bar is None

    def test_handles_no_total_bytes(self):
        from pipeline.downloader import _ProgressHook

        hook = _ProgressHook()
        hook({"status": "downloading", "downloaded_bytes": 500})
        # No bar created without total bytes
        assert hook.bar is None


# ---------------------------------------------------------------------------
# pipeline/transcriber.py – _format_srt_time
# ---------------------------------------------------------------------------


class TestFormatSrtTime:
    def test_zero_seconds(self):
        from pipeline.transcriber import _format_srt_time

        assert _format_srt_time(0.0) == "00:00:00,000"

    def test_simple_seconds(self):
        from pipeline.transcriber import _format_srt_time

        assert _format_srt_time(65.5) == "00:01:05,500"

    def test_hours(self):
        from pipeline.transcriber import _format_srt_time

        assert _format_srt_time(3661.123) == "01:01:01,123"

    def test_fractional_milliseconds(self):
        from pipeline.transcriber import _format_srt_time

        result = _format_srt_time(1.999)
        assert result == "00:00:01,999"


# ---------------------------------------------------------------------------
# pipeline/transcriber.py – _generate_srt
# ---------------------------------------------------------------------------


class TestGenerateSrt:
    def test_generates_srt_content(self):
        from pipeline.transcriber import _generate_srt

        segments = [
            {"start": 0.0, "end": 2.5, "text": " Hello world"},
            {"start": 2.5, "end": 5.0, "text": " How are you"},
        ]
        srt = _generate_srt(segments)
        assert "1\n00:00:00,000 --> 00:00:02,500\nHello world" in srt
        assert "2\n00:00:02,500 --> 00:00:05,000\nHow are you" in srt

    def test_empty_segments(self):
        from pipeline.transcriber import _generate_srt

        assert _generate_srt([]) == ""


# ---------------------------------------------------------------------------
# pipeline/transcriber.py – transcribe_audio (cached path)
# ---------------------------------------------------------------------------


class TestTranscribeAudioCached:
    def test_loads_from_disk_when_files_exist(self, tmp_path):
        from pipeline.transcriber import transcribe_audio

        audio_dir = tmp_path / "video"
        audio_dir.mkdir()
        audio_path = audio_dir / "audio.mp3"
        audio_path.write_text("")

        transcript_path = audio_dir / "transcript.txt"
        transcript_path.write_text("cached transcript text", encoding="utf-8")

        srt_path = audio_dir / "transcript.srt"
        srt_path.write_text("1\n00:00:00,000 --> 00:00:01,000\nHello", encoding="utf-8")

        result = transcribe_audio(str(audio_path))
        assert result["text"] == "cached transcript text"
        assert "Hello" in result["srt"]
        assert result["language"] == "unknown"
        assert result["segments"] == []

    def test_loads_cached_language(self, tmp_path):
        from pipeline.transcriber import transcribe_audio

        audio_dir = tmp_path / "video"
        audio_dir.mkdir()
        (audio_dir / "audio.mp3").write_text("")
        (audio_dir / "transcript.txt").write_text("texto", encoding="utf-8")
        (audio_dir / "transcript.srt").write_text("1\n00:00:00,000 --> 00:00:01,000\nHola", encoding="utf-8")
        (audio_dir / "language.txt").write_text("es", encoding="utf-8")

        result = transcribe_audio(str(audio_dir / "audio.mp3"))
        assert result["language"] == "es"

    def test_falls_back_to_unknown_without_language_file(self, tmp_path):
        from pipeline.transcriber import transcribe_audio

        audio_dir = tmp_path / "video"
        audio_dir.mkdir()
        (audio_dir / "audio.mp3").write_text("")
        (audio_dir / "transcript.txt").write_text("text", encoding="utf-8")
        (audio_dir / "transcript.srt").write_text("1\n00:00:00,000 --> 00:00:01,000\nHi", encoding="utf-8")

        result = transcribe_audio(str(audio_dir / "audio.mp3"))
        assert result["language"] == "unknown"


# ---------------------------------------------------------------------------
# pipeline/mindmap.py – _generate_markdown
# ---------------------------------------------------------------------------

SAMPLE_SKETCHNOTE_DATA = {
    "title": "Neural Networks",
    "sections": [
        {
            "id": "s1",
            "heading": "Architecture",
            "icon": "\U0001f3d7\ufe0f",
            "points": ["Layers organize neurons", "Deep vs shallow networks"],
            "color": "#4A90D9",
        },
        {
            "id": "s2",
            "heading": "Training",
            "icon": "\U0001f3cb\ufe0f",
            "points": ["Backpropagation", "Gradient descent optimization"],
            "color": "#E67E22",
        },
    ],
    "connections": [
        {"from": "s1", "to": "s2", "label": "feeds into"},
    ],
}


class TestGenerateMarkdown:
    def test_contains_title_as_heading(self):
        from pipeline.mindmap import _generate_markdown

        md = _generate_markdown(SAMPLE_SKETCHNOTE_DATA)
        assert md.startswith("# Neural Networks\n")

    def test_contains_section_headings_with_icons(self):
        from pipeline.mindmap import _generate_markdown

        md = _generate_markdown(SAMPLE_SKETCHNOTE_DATA)
        assert "\U0001f3d7\ufe0f Architecture" in md
        assert "\U0001f3cb\ufe0f Training" in md

    def test_contains_bullet_points(self):
        from pipeline.mindmap import _generate_markdown

        md = _generate_markdown(SAMPLE_SKETCHNOTE_DATA)
        assert "- Layers organize neurons" in md
        assert "- Backpropagation" in md

    def test_contains_connections(self):
        from pipeline.mindmap import _generate_markdown

        md = _generate_markdown(SAMPLE_SKETCHNOTE_DATA)
        assert "feeds into" in md


# ---------------------------------------------------------------------------
# pipeline/mindmap.py – _generate_html
# ---------------------------------------------------------------------------


class TestGenerateHtml:
    def test_contains_title(self):
        from pipeline.mindmap import _generate_html

        html = _generate_html(SAMPLE_SKETCHNOTE_DATA)
        assert "Neural Networks" in html

    def test_is_valid_html_structure(self):
        from pipeline.mindmap import _generate_html

        html = _generate_html(SAMPLE_SKETCHNOTE_DATA)
        assert html.startswith("<!DOCTYPE html>")
        assert "</html>" in html

    def test_contains_svg_element(self):
        from pipeline.mindmap import _generate_html

        html = _generate_html(SAMPLE_SKETCHNOTE_DATA)
        assert "<svg" in html
        assert "</svg>" in html

    def test_contains_section_headings(self):
        from pipeline.mindmap import _generate_html

        html = _generate_html(SAMPLE_SKETCHNOTE_DATA)
        assert "Architecture" in html
        assert "Training" in html

    def test_contains_sketchy_filter(self):
        from pipeline.mindmap import _generate_html

        html = _generate_html(SAMPLE_SKETCHNOTE_DATA)
        assert "feTurbulence" in html
        assert "feDisplacementMap" in html

    def test_contains_caveat_font(self):
        from pipeline.mindmap import _generate_html

        html = _generate_html(SAMPLE_SKETCHNOTE_DATA)
        assert "Caveat" in html

    def test_contains_connection_arrow(self):
        from pipeline.mindmap import _generate_html

        html = _generate_html(SAMPLE_SKETCHNOTE_DATA)
        assert "arrowhead" in html
        assert "feeds into" in html


# ---------------------------------------------------------------------------
# pipeline/mindmap.py – _call_claude (mocked API)
# ---------------------------------------------------------------------------


class TestCallClaude:
    @patch("pipeline.mindmap.anthropic.Anthropic")
    def test_parses_json_response(self, mock_anthropic_cls):
        from pipeline.mindmap import _call_claude

        mock_response = MagicMock()
        mock_response.content = [MagicMock(text=json.dumps(SAMPLE_SKETCHNOTE_DATA))]
        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_response
        mock_anthropic_cls.return_value = mock_client

        result = _call_claude("some transcript")
        assert result["title"] == "Neural Networks"
        assert len(result["sections"]) == 2

    @patch("pipeline.mindmap.anthropic.Anthropic")
    def test_handles_markdown_code_block_response(self, mock_anthropic_cls):
        from pipeline.mindmap import _call_claude

        wrapped = f"```json\n{json.dumps(SAMPLE_SKETCHNOTE_DATA)}\n```"
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text=wrapped)]
        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_response
        mock_anthropic_cls.return_value = mock_client

        result = _call_claude("some transcript")
        assert result["title"] == "Neural Networks"

    @patch("pipeline.mindmap.anthropic.Anthropic")
    def test_appends_language_instruction(self, mock_anthropic_cls):
        from pipeline.mindmap import _call_claude

        mock_response = MagicMock()
        mock_response.content = [MagicMock(text=json.dumps(SAMPLE_SKETCHNOTE_DATA))]
        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_response
        mock_anthropic_cls.return_value = mock_client

        _call_claude("some transcript", language="Spanish")

        call_args = mock_client.messages.create.call_args
        content = call_args.kwargs["messages"][0]["content"]
        assert "Write ALL content" in content
        assert "in Spanish" in content

    @patch("pipeline.mindmap.anthropic.Anthropic")
    def test_no_language_instruction_when_empty(self, mock_anthropic_cls):
        from pipeline.mindmap import _call_claude

        mock_response = MagicMock()
        mock_response.content = [MagicMock(text=json.dumps(SAMPLE_SKETCHNOTE_DATA))]
        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_response
        mock_anthropic_cls.return_value = mock_client

        _call_claude("some transcript", language="")

        call_args = mock_client.messages.create.call_args
        content = call_args.kwargs["messages"][0]["content"]
        assert "Write ALL content" not in content

    @patch("pipeline.mindmap.anthropic.Anthropic")
    def test_no_language_instruction_when_unknown(self, mock_anthropic_cls):
        from pipeline.mindmap import _call_claude

        mock_response = MagicMock()
        mock_response.content = [MagicMock(text=json.dumps(SAMPLE_SKETCHNOTE_DATA))]
        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_response
        mock_anthropic_cls.return_value = mock_client

        _call_claude("some transcript", language="unknown")

        call_args = mock_client.messages.create.call_args
        content = call_args.kwargs["messages"][0]["content"]
        assert "Write ALL content" not in content

    @patch("pipeline.mindmap.anthropic.Anthropic")
    def test_truncates_long_transcript(self, mock_anthropic_cls):
        from pipeline.mindmap import MAX_TRANSCRIPT_LENGTH, _call_claude

        mock_response = MagicMock()
        mock_response.content = [MagicMock(text=json.dumps(SAMPLE_SKETCHNOTE_DATA))]
        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_response
        mock_anthropic_cls.return_value = mock_client

        long_text = "x" * (MAX_TRANSCRIPT_LENGTH + 5000)
        _call_claude(long_text)

        call_args = mock_client.messages.create.call_args
        content = call_args.kwargs["messages"][0]["content"]
        assert "[...transcript truncated...]" in content


# ---------------------------------------------------------------------------
# pipeline/mindmap.py – generate_mindmap (full integration, mocked API)
# ---------------------------------------------------------------------------


class TestGenerateMindmap:
    @patch("pipeline.mindmap._call_claude", return_value=SAMPLE_SKETCHNOTE_DATA)
    def test_generates_all_formats(self, mock_claude, tmp_path):
        from pipeline.mindmap import generate_mindmap

        result = generate_mindmap("test transcript", str(tmp_path), formats="all")
        assert "json_path" in result
        assert "md_path" in result
        assert "html_path" in result
        assert os.path.exists(result["json_path"])
        assert os.path.exists(result["md_path"])
        assert os.path.exists(result["html_path"])

    @patch("pipeline.mindmap._call_claude", return_value=SAMPLE_SKETCHNOTE_DATA)
    def test_generates_json_only(self, mock_claude, tmp_path):
        from pipeline.mindmap import generate_mindmap

        result = generate_mindmap("test transcript", str(tmp_path), formats="json")
        assert "json_path" in result
        assert os.path.exists(result["json_path"])

        with open(result["json_path"]) as f:
            data = json.load(f)
        assert data["title"] == "Neural Networks"

    @patch("pipeline.mindmap._call_claude", return_value=SAMPLE_SKETCHNOTE_DATA)
    def test_generates_md_only(self, mock_claude, tmp_path):
        from pipeline.mindmap import generate_mindmap

        result = generate_mindmap("test transcript", str(tmp_path), formats="md")
        assert "md_path" in result
        assert os.path.exists(result["md_path"])

        with open(result["md_path"]) as f:
            content = f.read()
        assert "# Neural Networks" in content

    @patch("pipeline.mindmap._call_claude", return_value=SAMPLE_SKETCHNOTE_DATA)
    def test_html_contains_svg(self, mock_claude, tmp_path):
        from pipeline.mindmap import generate_mindmap

        result = generate_mindmap("test transcript", str(tmp_path), formats="html")
        assert "html_path" in result

        with open(result["html_path"]) as f:
            content = f.read()
        assert "<svg" in content


# ---------------------------------------------------------------------------
# pipeline/extractor.py – extract_audio_from_folder
# ---------------------------------------------------------------------------


class TestExtractAudioFromFolder:
    def test_returns_empty_for_invalid_directory(self):
        from pipeline.extractor import extract_audio_from_folder

        result = extract_audio_from_folder("/nonexistent/path", "/tmp/out")
        assert result == []

    def test_returns_empty_for_no_video_files(self, tmp_path):
        from pipeline.extractor import extract_audio_from_folder

        (tmp_path / "readme.txt").write_text("not a video")
        result = extract_audio_from_folder(str(tmp_path), str(tmp_path / "out"))
        assert result == []

    @patch("pipeline.extractor.extract_audio_from_file")
    def test_processes_supported_extensions(self, mock_extract, tmp_path):
        from pipeline.extractor import extract_audio_from_folder

        # Create fake video files
        (tmp_path / "video1.mp4").write_text("")
        (tmp_path / "video2.mkv").write_text("")
        (tmp_path / "notes.txt").write_text("")

        out_dir = str(tmp_path / "output")
        mock_extract.return_value = {"title": "test", "audio_path": "/fake/audio.mp3"}

        results = extract_audio_from_folder(str(tmp_path), out_dir)
        # Should be called for .mp4 and .mkv, not .txt
        assert mock_extract.call_count == 2
        assert len(results) == 2


# ---------------------------------------------------------------------------
# pipeline/extractor.py – extract_audio_from_file
# ---------------------------------------------------------------------------


class TestExtractAudioFromFile:
    def test_returns_cached_when_audio_exists(self, tmp_path):
        from pipeline.extractor import extract_audio_from_file

        out_dir = tmp_path / "output"
        video_dir = out_dir / "myvideo"
        video_dir.mkdir(parents=True)
        (video_dir / "audio.mp3").write_text("fake audio")

        result = extract_audio_from_file(str(tmp_path / "myvideo.mp4"), str(out_dir))
        assert result is not None
        assert result["title"] == "myvideo"

    @patch("pipeline.extractor.ffmpeg")
    def test_returns_none_on_ffmpeg_error(self, mock_ffmpeg, tmp_path):
        import ffmpeg as real_ffmpeg

        mock_ffmpeg.Error = real_ffmpeg.Error
        mock_ffmpeg.input.return_value.output.return_value.overwrite_output.return_value.run.side_effect = (
            real_ffmpeg.Error("ffmpeg", b"", b"error")
        )

        from pipeline.extractor import extract_audio_from_file

        result = extract_audio_from_file(
            str(tmp_path / "broken.mp4"), str(tmp_path / "output")
        )
        assert result is None


# ---------------------------------------------------------------------------
# main.py – parse_args
# ---------------------------------------------------------------------------


class TestParseArgs:
    def test_parses_url_argument(self, monkeypatch):
        monkeypatch.setattr(
            "sys.argv",
            ["main.py", "--url", "https://youtube.com/watch?v=abc"],
        )
        from main import parse_args

        args = parse_args()
        assert args.url == "https://youtube.com/watch?v=abc"
        assert args.folder is None

    def test_parses_folder_argument(self, monkeypatch):
        monkeypatch.setattr("sys.argv", ["main.py", "--folder", "/my/videos"])
        from main import parse_args

        args = parse_args()
        assert args.folder == "/my/videos"
        assert args.url is None

    def test_default_model_is_base(self, monkeypatch):
        monkeypatch.setattr(
            "sys.argv",
            ["main.py", "--url", "https://youtube.com/watch?v=abc"],
        )
        from main import parse_args

        args = parse_args()
        assert args.model == "base"

    def test_url_and_folder_are_mutually_exclusive(self, monkeypatch):
        monkeypatch.setattr(
            "sys.argv",
            ["main.py", "--url", "http://x.com", "--folder", "/path"],
        )
        from main import parse_args

        with pytest.raises(SystemExit):
            parse_args()


# ---------------------------------------------------------------------------
# main.py – process_video
# ---------------------------------------------------------------------------


class TestProcessVideo:
    @patch("main.generate_mindmap")
    @patch("main.transcribe_audio")
    def test_skips_mindmap_for_short_transcript(self, mock_transcribe, mock_mindmap):
        from main import process_video

        mock_transcribe.return_value = {"text": "too short"}

        process_video(
            title="Test",
            audio_path="/fake/audio.mp3",
            model_name="base",
            language="auto",
            output_format="all",
            open_browser=False,
        )
        mock_mindmap.assert_not_called()

    @patch("main.generate_mindmap")
    @patch("main.transcribe_audio")
    def test_calls_mindmap_for_normal_transcript(self, mock_transcribe, mock_mindmap):
        from main import process_video

        mock_transcribe.return_value = {"text": "A" * 100, "language": "Spanish"}
        mock_mindmap.return_value = {"html_path": None}

        process_video(
            title="Test",
            audio_path="/fake/audio.mp3",
            model_name="base",
            language="auto",
            output_format="all",
            open_browser=False,
        )
        mock_mindmap.assert_called_once()
        _, kwargs = mock_mindmap.call_args
        assert kwargs["language"] == "Spanish"
