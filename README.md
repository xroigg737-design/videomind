# VideoMind

Process video content and generate interactive visual concept maps.

VideoMind extracts audio from YouTube videos or local files, transcribes them using OpenAI Whisper, and generates structured concept maps powered by Claude AI.

## Features

- **YouTube support** - Single videos or entire playlists via `yt-dlp`
- **Local video support** - Process `.mp4`, `.avi`, `.mkv`, `.mov`, `.webm` files
- **Whisper transcription** - Local, offline, no API costs. Choose model size (tiny → large)
- **Auto language detection** - Or force a specific language
- **Concept map generation** - Claude analyzes transcripts and extracts key concepts
- **Web UI** - Flask-based interface with real-time progress streaming (SSE)
- **Three output formats**:
  - **HTML** - SVG-based sketchnote with hand-drawn styling, openable in any browser
  - **Markdown** - Markmap-compatible indented mind map
  - **JSON** - Structured data for import into XMind, MindNode, Obsidian Canvas

## Requirements

### System Dependencies

**ffmpeg** must be installed on your system:

```bash
# Ubuntu / Debian
sudo apt install ffmpeg

# macOS (Homebrew)
brew install ffmpeg

# Windows (Chocolatey)
choco install ffmpeg
```

**Python 3.10+** is required.

### API Keys

Set your Anthropic API key as an environment variable or in a `.env` file:

```bash
# Environment variable
export ANTHROPIC_API_KEY="sk-ant-..."

# Or create a .env file in the project root
echo 'ANTHROPIC_API_KEY=sk-ant-...' > .env
```

## Installation

```bash
# Clone or download the project
cd videomind

# Create a virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # Linux/macOS
# venv\Scripts\activate   # Windows

# Install dependencies
pip install -r requirements.txt
```

> **Note**: `openai-whisper` will install PyTorch as a dependency. If you have a CUDA-compatible GPU, install the CUDA version of PyTorch first for faster transcription: https://pytorch.org/get-started/locally/

## Usage

### Web UI

```bash
python app.py
```

Open http://localhost:5000 in your browser. The web interface lets you submit YouTube URLs or local paths, shows real-time processing logs, and includes a library to browse all previously processed videos.

### CLI

#### YouTube Video

```bash
python main.py --url "https://youtube.com/watch?v=VIDEO_ID" --model base
```

#### YouTube Playlist

```bash
python main.py --url "https://youtube.com/playlist?list=PLAYLIST_ID" --model small
```

#### Local Video Folder

```bash
python main.py --folder /path/to/videos --model base
```

#### All Options

```
python main.py --help

Options:
  --url URL             YouTube URL (single video or playlist)
  --folder PATH         Local folder path containing video files
  --model MODEL         Whisper model: tiny|base|small|medium|large (default: base)
  --lang LANG           Force language (default: auto-detect)
  --output DIR          Output directory (default: ./output)
  --format FORMAT       Output format: all|html|md|json (default: all)
  --open                Auto-open HTML result in browser
```

#### Examples

```bash
# Quick processing with tiny model, only HTML output
python main.py --url "https://youtu.be/dQw4w9WgXcQ" --model tiny --format html --open

# Spanish video, medium model, custom output dir
python main.py --url "https://youtube.com/watch?v=..." --model medium --lang es --output ./results

# Process all videos in a folder
python main.py --folder ~/Downloads/lectures --model small --format all
```

## Output Structure

For each processed video, files are saved under the output directory:

```
output/
└── Video Title/
    ├── audio.mp3           # Extracted audio (16kHz mono)
    ├── transcript.txt      # Full transcript text
    ├── transcript.srt      # SRT subtitles with timestamps
    ├── mindmap.md          # Markmap-compatible markdown
    ├── mindmap.html        # Interactive visual map (open in browser)
    └── mindmap.json        # Structured JSON for tool import
```

## Whisper Model Comparison

| Model  | Size   | Speed    | Accuracy | VRAM  |
|--------|--------|----------|----------|-------|
| tiny   | 39 MB  | Fastest  | Basic    | ~1 GB |
| base   | 74 MB  | Fast     | Good     | ~1 GB |
| small  | 244 MB | Moderate | Better   | ~2 GB |
| medium | 769 MB | Slow     | Great    | ~5 GB |
| large  | 1.5 GB | Slowest  | Best     | ~10 GB|

Use `tiny` or `base` for quick tests, `small` or `medium` for production quality.

## Project Structure

```
videomind/
├── main.py                 # CLI entry point
├── app.py                  # Flask web UI with SSE streaming
├── config.py               # Configuration (models, API key, defaults)
├── requirements.txt        # Python dependencies
├── .env                    # ANTHROPIC_API_KEY (not committed)
├── pipeline/
│   ├── downloader.py       # YouTube audio download via yt-dlp
│   ├── extractor.py        # Local video audio extraction via ffmpeg
│   ├── transcriber.py      # Whisper speech-to-text
│   └── mindmap.py          # Claude-powered sketchnote generation
├── templates/              # Flask HTML templates
│   ├── base.html
│   ├── index.html
│   ├── status.html
│   ├── library.html
│   └── viewer.html
├── tests/
│   └── test_videomind.py   # Pytest test suite
└── output/                 # Generated outputs (per video)
```

## Configuration

Settings are defined in `config.py`:

| Setting | Default | Description |
|---------|---------|-------------|
| `CLAUDE_MODEL` | `claude-sonnet-4-5-20250929` | Claude model for sketchnote generation |
| `DEFAULT_WHISPER_MODEL` | `base` | Whisper model size |
| `DEFAULT_OUTPUT_DIR` | `./output` | Output directory |
| `AUDIO_SAMPLE_RATE` | `16000` | Audio sample rate (Hz) |
| `AUDIO_CHANNELS` | `1` | Mono audio |
| `AUDIO_FORMAT` | `mp3` | Audio output format |
| `SUPPORTED_VIDEO_EXTENSIONS` | `.mp4, .avi, .mkv, .mov, .webm` | Accepted video formats |

## Tests

Run the test suite with pytest:

```bash
pytest tests/
```

## Troubleshooting

### "ffmpeg not found"
Install ffmpeg system-wide (see Requirements above). Verify with `ffmpeg -version`.

### "ANTHROPIC_API_KEY not set"
Set the key in your environment or create a `.env` file in the project root.

### Whisper runs very slowly
- Use a smaller model (`--model tiny` or `--model base`)
- If you have an NVIDIA GPU, install the CUDA version of PyTorch
- CPU-only transcription of long videos with `medium`/`large` models can take a long time

### YouTube download fails
- Update yt-dlp: `pip install -U yt-dlp`
- Check that the URL is valid and the video is publicly accessible
- Some videos may have regional restrictions or require authentication

### Mind map generation fails
- Verify your `ANTHROPIC_API_KEY` is valid and has sufficient credits
- Very short transcripts (< 20 characters) are skipped automatically
- Long transcripts are automatically truncated to fit within API limits

## License

MIT
