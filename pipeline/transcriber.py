"""Audio transcription using OpenAI Whisper (local model).

Produces a full transcript text file and an SRT subtitle file.
"""

import os

# Force CPU mode — CUDA can crash with bus errors on WSL2 even when
# torch.cuda.is_available() reports True and basic ops succeed.
os.environ["CUDA_VISIBLE_DEVICES"] = ""

import whisper


def _format_srt_time(seconds: float) -> str:
    """Convert seconds to SRT timestamp format HH:MM:SS,mmm."""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int((seconds - int(seconds)) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def _generate_srt(segments: list[dict]) -> str:
    """Generate SRT content from Whisper segments."""
    lines = []
    for i, seg in enumerate(segments, 1):
        start = _format_srt_time(seg["start"])
        end = _format_srt_time(seg["end"])
        text = seg["text"].strip()
        lines.append(f"{i}\n{start} --> {end}\n{text}\n")
    return "\n".join(lines)


def transcribe_audio(
    audio_path: str,
    model_name: str = "base",
    language: str = "auto",
) -> dict:
    """Transcribe an audio file using Whisper.

    Args:
        audio_path: Path to the audio file.
        model_name: Whisper model size (tiny/base/small/medium/large).
        language: Language code or "auto" for auto-detection.

    Returns:
        {
            "text": str,          # Full transcript
            "srt": str,           # SRT subtitle content
            "language": str,      # Detected language
            "segments": list,     # Raw Whisper segments
        }
    """
    output_dir = os.path.dirname(audio_path)
    transcript_path = os.path.join(output_dir, "transcript.txt")
    srt_path = os.path.join(output_dir, "transcript.srt")
    lang_path = os.path.join(output_dir, "language.txt")

    # Check if already transcribed
    if os.path.exists(transcript_path) and os.path.exists(srt_path):
        print("  Transcript already exists, loading from disk...")
        with open(transcript_path, "r", encoding="utf-8") as f:
            text = f.read()
        with open(srt_path, "r", encoding="utf-8") as f:
            srt = f.read()
        cached_lang = "unknown"
        if os.path.exists(lang_path):
            with open(lang_path, "r", encoding="utf-8") as f:
                cached_lang = f.read().strip() or "unknown"
        return {"text": text, "srt": srt, "language": cached_lang, "segments": []}

    print(f"  Loading Whisper model: {model_name} (device: cpu)")
    model = whisper.load_model(model_name, device="cpu")

    print("  Transcribing audio (this may take a while)...")
    transcribe_opts = {}
    if language != "auto":
        transcribe_opts["language"] = language

    result = model.transcribe(
        audio_path,
        verbose=False,
        fp16=False,
        **transcribe_opts,
    )

    detected_lang = result.get("language", "unknown")
    full_text = result["text"].strip()
    segments = result.get("segments", [])
    srt_content = _generate_srt(segments)

    # Write output files
    with open(transcript_path, "w", encoding="utf-8") as f:
        f.write(full_text)
    print(f"  Saved: {transcript_path}")

    with open(srt_path, "w", encoding="utf-8") as f:
        f.write(srt_content)
    print(f"  Saved: {srt_path}")

    with open(lang_path, "w", encoding="utf-8") as f:
        f.write(detected_lang)

    print(f"  Detected language: {detected_lang}")
    print(f"  Transcript length: {len(full_text)} characters")

    return {
        "text": full_text,
        "srt": srt_content,
        "language": detected_lang,
        "segments": segments,
    }
