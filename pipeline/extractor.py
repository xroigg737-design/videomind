"""Audio extraction from local video files using ffmpeg-python.

Converts video files to 16 kHz mono MP3 optimized for transcription.
"""

import os

import ffmpeg
from tqdm import tqdm

from config import SUPPORTED_VIDEO_EXTENSIONS


def extract_audio_from_file(video_path: str, output_dir: str) -> dict | None:
    """Extract audio from a single local video file.

    Returns {"title": str, "audio_path": str} or None on failure.
    """
    basename = os.path.splitext(os.path.basename(video_path))[0]
    video_dir = os.path.join(output_dir, basename)
    os.makedirs(video_dir, exist_ok=True)
    audio_path = os.path.join(video_dir, "audio.mp3")

    if os.path.exists(audio_path):
        print(f"  Audio already exists, skipping: {basename}")
        return {"title": basename, "audio_path": audio_path}

    print(f"  Extracting audio: {basename}")
    try:
        (
            ffmpeg.input(video_path)
            .output(
                audio_path,
                acodec="libmp3lame",
                ar=16000,
                ac=1,
                audio_bitrate="192k",
            )
            .overwrite_output()
            .run(quiet=True)
        )
    except ffmpeg.Error as e:
        print(f"  Error extracting audio from '{video_path}': {e}")
        return None

    if os.path.exists(audio_path):
        return {"title": basename, "audio_path": audio_path}

    print(f"  Warning: audio file not created for '{video_path}'")
    return None


def extract_audio_from_folder(folder_path: str, output_dir: str) -> list[dict]:
    """Extract audio from all supported video files in a folder.

    Returns a list of dicts: [{"title": str, "audio_path": str}, ...]
    """
    if not os.path.isdir(folder_path):
        print(f"Error: '{folder_path}' is not a valid directory.")
        return []

    video_files = sorted(
        f
        for f in os.listdir(folder_path)
        if os.path.splitext(f)[1].lower() in SUPPORTED_VIDEO_EXTENSIONS
    )

    if not video_files:
        print(f"No supported video files found in '{folder_path}'.")
        print(f"Supported formats: {', '.join(sorted(SUPPORTED_VIDEO_EXTENSIONS))}")
        return []

    results = []
    for filename in tqdm(video_files, desc="Extracting audio", unit="file"):
        video_path = os.path.join(folder_path, filename)
        result = extract_audio_from_file(video_path, output_dir)
        if result:
            results.append(result)

    return results
