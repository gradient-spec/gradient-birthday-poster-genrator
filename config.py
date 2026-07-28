from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent

# ── Poster template ───────────────────────────────────────────────────────────
TEMPLATE_PATH = BASE_DIR / "templates" / "1.png"

# ── Member photo (local fallback, Supabase URL is preferred at runtime) ───────
PHOTO_FOLDER = BASE_DIR / "photos"

# ── Generated poster output ───────────────────────────────────────────────────
OUTPUT_FOLDER = BASE_DIR / "output"

# ── Photo placement on poster (pixels) ───────────────────────────────────────
PHOTO_X = 178
PHOTO_Y = 618
PHOTO_WIDTH = 542
PHOTO_HEIGHT = 544
PHOTO_CORNER_RADIUS = 0

# ── Name text rendering ───────────────────────────────────────────────────────
FONT_PATH = BASE_DIR / "fonts" / "birthstone.ttf"
FONT_SIZE = 100
FONT_COLOR = (0, 0, 0)
NAME_CENTER_X = 454
NAME_Y = 1190

# ── Telegram (overridable at runtime from app_settings in Supabase) ───────────
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
