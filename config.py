"""
config.py — Central configuration for StoryMaker 3.
Loads environment variables from .env and exports all constants.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# ─── Load .env ───────────────────────────────────────────────────────
load_dotenv()

# ─── Project Paths ───────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).parent.resolve()
OUTPUT_DIR = PROJECT_ROOT / "output"
STORY_BANK_PATH = PROJECT_ROOT / "story_bank.json"
USED_STORIES_PATH = PROJECT_ROOT / "used_stories.json"
SCHEDULE_LOG_PATH = PROJECT_ROOT / "scheduled_videos.json"

# ─── Video Settings (Short-Form 9:16) ────────────────────────────────
VIDEO_WIDTH = 1080
VIDEO_HEIGHT = 1920
VIDEO_FPS = 24
VIDEO_CODEC = "libx264"
AUDIO_CODEC = "aac"

# ─── Video Settings (Long-Form 16:9) ────────────────────────────────
LONG_VIDEO_WIDTH = 1920
LONG_VIDEO_HEIGHT = 1080

# ─── TTS Settings ────────────────────────────────────────────────────
TTS_VOICE = "en-US-AnaNeural"   # Cheerful, child-friendly Microsoft voice
TTS_RATE = "+10%"                # Slightly faster for engagement

# ─── Subtitle / Font Settings ────────────────────────────────────────
FONTS_DIR = PROJECT_ROOT / "fonts"
# Arial Bold is built into every Windows installation — no download needed.
# PIL loads it directly from C:\Windows\Fonts.
FONT_PATH = str(FONTS_DIR / "Arimo-Bold.ttf")
FONT_SIZE = 50  # Larger for YouTube Shorts readability
FONT_COLOR = "white" 
STROKE_COLOR = "black"
STROKE_WIDTH = 4  # Thick outline for crisp contrast at 1080x1920
SUBTITLE_Y_POSITION = int(VIDEO_HEIGHT * 0.70)  # Just below center line

# ─── Long-Form Subtitle / Font Settings ──────────────────────────────
LONG_FONT_SIZE = 60
LONG_SUBTITLE_Y_POSITION = int(LONG_VIDEO_HEIGHT * 0.85)

# ─── Ken Burns Effect (Short-Form) ───────────────────────────────────
ZOOM_START = 1.0
ZOOM_END = 1.2

# ─── Ken Burns Effect (Long-Form) ──────────────────
LONG_ZOOM_START = 1.0
LONG_ZOOM_END = 1.2

# ─── Long-Form Image Stretch ─────────────────────────────────────────
# Horizontal stretch factor applied to source images before contain-fit.
# 1.25 converts a 1:1 square image into 5:4 aspect ratio.
LONG_IMAGE_STRETCH_X = 1.25

# ─── YouTube Upload ──────────────────────────────────────────────────
YOUTUBE_CLIENT_SECRETS = os.getenv(
    "YOUTUBE_CLIENT_SECRETS_PATH",
    str(PROJECT_ROOT / "client_secrets.json"),
)
YOUTUBE_TOKEN_PATH = str(PROJECT_ROOT / "youtube_token.json")
YOUTUBE_CATEGORY_ID = "24"      # Entertainment
YOUTUBE_PRIVACY = "public"

# ─── Pollinations.ai ─────────────────────────────────────────────────
IMAGE_API_URL = "https://image.pollinations.ai/prompt/{prompt}?width={w}&height={h}&nologo=true&model=flux"
IMAGE_RETRY_ATTEMPTS = 5
IMAGE_RETRY_DELAY = 10          # seconds between retries
