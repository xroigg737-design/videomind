"""YouTube video/playlist downloader using yt-dlp.

Downloads audio-only streams from YouTube URLs (single videos or playlists).
"""

import os
import re

from tqdm import tqdm
import yt_dlp


def sanitize_filename(name: str) -> str:
    """Remove or replace characters that are unsafe for filenames."""
    name = re.sub(r'[<>:"/\\|?*]', "", name)
    name = name.strip(". ")
    return name[:200] if name else "untitled"


class _ProgressHook:
    """yt-dlp progress hook that drives a tqdm bar."""

    def __init__(self):
        self.bar: tqdm | None = None

    def __call__(self, d: dict):
        if d["status"] == "downloading":
            total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
            downloaded = d.get("downloaded_bytes", 0)
            if self.bar is None and total:
                self.bar = tqdm(
                    total=total,
                    unit="B",
                    unit_scale=True,
                    desc="Downloading",
                )
            if self.bar:
                self.bar.n = downloaded
                self.bar.refresh()
        elif d["status"] == "finished":
            if self.bar:
                self.bar.close()
                self.bar = None


def download_audio(url: str, output_dir: str) -> list[dict]:
    """Download audio from a YouTube URL (video or playlist).

    Returns a list of dicts: [{"title": str, "audio_path": str}, ...]
    """
    os.makedirs(output_dir, exist_ok=True)

    # First pass: extract info to discover entries
    with yt_dlp.YoutubeDL({"quiet": True, "extract_flat": True}) as ydl:
        info = ydl.extract_info(url, download=False)

    entries = info.get("entries", [info])  # playlist or single video
    results = []

    for entry in entries:
        video_url = entry.get("url") or entry.get("webpage_url") or url
        title = sanitize_filename(entry.get("title", "untitled"))
        video_dir = os.path.join(output_dir, title)
        os.makedirs(video_dir, exist_ok=True)
        audio_path = os.path.join(video_dir, "audio.mp3")

        if os.path.exists(audio_path):
            print(f"  Audio already exists, skipping download: {title}")
            results.append({"title": title, "audio_path": audio_path})
            continue

        hook = _ProgressHook()
        ydl_opts = {
            "format": "bestaudio/best",
            "outtmpl": os.path.join(video_dir, "audio.%(ext)s"),
            "postprocessors": [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "192",
                }
            ],
            "postprocessor_args": [
                "-ar",
                "16000",
                "-ac",
                "1",
            ],
            "progress_hooks": [hook],
            "quiet": True,
            "no_warnings": True,
        }

        print(f"\n  Downloading: {title}")
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([video_url])
        except yt_dlp.utils.DownloadError as e:
            print(f"  Error downloading '{title}': {e}")
            continue

        if os.path.exists(audio_path):
            results.append({"title": title, "audio_path": audio_path})
        else:
            # yt-dlp may use a slightly different output name
            for f in os.listdir(video_dir):
                if f.endswith(".mp3"):
                    actual = os.path.join(video_dir, f)
                    os.rename(actual, audio_path)
                    results.append({"title": title, "audio_path": audio_path})
                    break
            else:
                print(f"  Warning: audio file not found after download for '{title}'")

    return results
