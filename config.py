from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
EXCEL_PATH = DATA_DIR / "members.xlsx"
TEMPLATE_PATH = BASE_DIR / "templates" / "1.png"
PHOTO_FOLDER = BASE_DIR / "photos"
OUTPUT_FOLDER = BASE_DIR / "output"

PHOTO_X = 178
PHOTO_Y = 618
PHOTO_WIDTH = 542
PHOTO_HEIGHT = 544
PHOTO_CORNER_RADIUS = 0

FONT_PATH = BASE_DIR / "fonts" / "birthstone.ttf"
FONT_SIZE = 100
FONT_COLOR = (0, 0, 0)
NAME_CENTER_X = 454
NAME_Y = 1190

REQUIRED_COLUMNS = ("Name", "Birthday", "Photo")

import os
from dotenv import load_dotenv

load_dotenv()
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
