"""Configuration management for VideoMind.

Reads API keys and settings from environment variables or a .env file.
"""

import os
import sys

from dotenv import load_dotenv

load_dotenv()

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

# Azure OpenAI settings
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT", "")
AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY", "")
AZURE_OPENAI_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-01")

# Anthropic model for concept map generation
CLAUDE_MODEL = "claude-sonnet-4-5-20250929"

# DALL-E settings
DALLE_MODEL = "dall-e-3"
DALLE_QUALITY = "standard"

# Default settings
DEFAULT_WHISPER_MODEL = "base"
DEFAULT_LANGUAGE = "auto"
DEFAULT_OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "output")
DEFAULT_FORMAT = "all"
DEFAULT_VISUAL_TYPE = "sketchnote"

# Audio extraction settings
AUDIO_SAMPLE_RATE = 16000
AUDIO_CHANNELS = 1
AUDIO_FORMAT = "mp3"

# Supported local video extensions
SUPPORTED_VIDEO_EXTENSIONS = {".mp4", ".avi", ".mkv", ".mov", ".webm"}


def validate_config():
    """Check that required configuration is present."""
    if not ANTHROPIC_API_KEY:
        print(
            "Error: ANTHROPIC_API_KEY not set. "
            "Set it as an environment variable or in a .env file.",
            file=sys.stderr,
        )
        return False
    return True


def validate_dalle_config():
    """Check that DALL-E configuration is present. Returns True if ready."""
    if not OPENAI_API_KEY:
        print(
            "  Warning: OPENAI_API_KEY not set. "
            "DALL-E image generation will be skipped."
        )
        return False
    return True
