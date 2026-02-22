#!/usr/bin/env python3
"""VideoMind - Video content to visual concept maps.

CLI entry point that orchestrates the full pipeline:
  1. Download/extract audio from video sources
  2. Transcribe audio to text using Whisper
  3. Generate interactive concept maps using Claude
"""

import argparse
import os
import sys
import webbrowser

# Allow running from the project directory
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import DEFAULT_OUTPUT_DIR, DEFAULT_VISUAL_TYPE, DEFAULT_WHISPER_MODEL, validate_config
from pipeline.downloader import download_audio
from pipeline.extractor import extract_audio_from_folder
from pipeline.transcriber import transcribe_audio
from pipeline.formats import generate_visual_format


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="videomind",
        description="VideoMind: Process video content and generate visual concept maps.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
Examples:
  python main.py --url "https://youtube.com/watch?v=dQw4w9WgXcQ" --model base
  python main.py --folder ./my_videos --model small --format html --open
  python main.py --url "https://youtube.com/playlist?list=..." --model medium
        """,
    )

    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument(
        "--url",
        type=str,
        help="YouTube URL (single video or playlist)",
    )
    source.add_argument(
        "--folder",
        type=str,
        help="Local folder containing video files, or a single video file path",
    )

    parser.add_argument(
        "--model",
        type=str,
        choices=["tiny", "base", "small", "medium", "large"],
        default=DEFAULT_WHISPER_MODEL,
        help=f"Whisper model size (default: {DEFAULT_WHISPER_MODEL})",
    )
    parser.add_argument(
        "--lang",
        type=str,
        default="auto",
        help="Force transcription language (default: auto-detect)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=DEFAULT_OUTPUT_DIR,
        help=f"Output directory (default: {DEFAULT_OUTPUT_DIR})",
    )
    parser.add_argument(
        "--format",
        type=str,
        choices=["all", "html", "md", "json"],
        default="all",
        help="Mind map output format (default: all)",
    )
    parser.add_argument(
        "--visual-type",
        type=str,
        choices=["sketchnote", "mindmap", "infografia"],
        default=DEFAULT_VISUAL_TYPE,
        help=f"Visual format type (default: {DEFAULT_VISUAL_TYPE})",
    )
    parser.add_argument(
        "--open",
        action="store_true",
        dest="open_browser",
        help="Auto-open HTML result in browser",
    )

    return parser.parse_args()


def process_video(
    title: str,
    audio_path: str,
    model_name: str,
    language: str,
    output_format: str,
    open_browser: bool,
    visual_type: str = DEFAULT_VISUAL_TYPE,
):
    """Run the transcription + visual format pipeline for one video."""
    video_dir = os.path.dirname(audio_path)

    print(f"\n{'='*60}")
    print(f"  Processing: {title}")
    print(f"{'='*60}")

    # Step 1: Transcribe
    print("\n[1/2] Transcribing audio...")
    result = transcribe_audio(audio_path, model_name=model_name, language=language)
    transcript = result["text"]

    if not transcript or len(transcript.strip()) < 20:
        print("  Warning: Transcript is very short or empty. Skipping visual format.")
        return

    # Step 2: Generate visual format
    print(f"\n[2/2] Generating {visual_type}...")
    detected_language = result.get("language", "")
    try:
        mm_result = generate_visual_format(
            transcript, video_dir,
            format_type=visual_type,
            formats=output_format,
            language=detected_language,
        )
    except Exception as e:
        print(f"  Error generating {visual_type}: {e}")
        return

    # Open in browser if requested
    html_path = mm_result.get("html_path")
    if open_browser and html_path and os.path.exists(html_path):
        print(f"\n  Opening in browser: {html_path}")
        webbrowser.open(f"file://{os.path.abspath(html_path)}")

    print(f"\n  Done! Output: {video_dir}/")


def main():
    args = parse_args()

    print("""
 __      ___     _           __  __ _           _
 \\ \\    / (_)   | |         |  \\/  (_)         | |
  \\ \\  / / _  __| | ___  ___| \\  / |_ _ __   __| |
   \\ \\/ / | |/ _` |/ _ \\/ _ \\ |\\/| | | '_ \\ / _` |
    \\  /  | | (_| |  __/ (_) | |  | | | | | | (_| |
     \\/   |_|\\__,_|\\___|\\___/|_|  |_|_|_| |_|\\__,_|
    """)

    if not validate_config():
        sys.exit(1)

    output_dir = os.path.abspath(args.output)
    os.makedirs(output_dir, exist_ok=True)

    # Step 1: Get audio files
    print("\n[Step 1] Obtaining audio from source...")
    if args.url:
        try:
            videos = download_audio(args.url, output_dir)
        except Exception as e:
            print(f"Error downloading from URL: {e}")
            sys.exit(1)
    elif os.path.isfile(os.path.abspath(args.folder)):
        filepath = os.path.abspath(args.folder)
        try:
            from pipeline.extractor import extract_audio_from_file
            result = extract_audio_from_file(filepath, output_dir)
            videos = [result] if result else []
        except Exception as e:
            print(f"Error extracting audio from file: {e}")
            sys.exit(1)
    else:
        folder = os.path.abspath(args.folder)
        try:
            videos = extract_audio_from_folder(folder, output_dir)
        except Exception as e:
            print(f"Error extracting audio from folder: {e}")
            sys.exit(1)

    if not videos:
        print("\nNo videos to process. Exiting.")
        sys.exit(1)

    print(f"\n  Found {len(videos)} video(s) to process.")

    # Step 2-3: Process each video
    for video in videos:
        process_video(
            title=video["title"],
            audio_path=video["audio_path"],
            model_name=args.model,
            language=args.lang,
            output_format=args.format,
            open_browser=args.open_browser,
            visual_type=args.visual_type,
        )

    print(f"\n{'='*60}")
    print(f"  All done! Output directory: {output_dir}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
