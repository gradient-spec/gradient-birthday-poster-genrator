from __future__ import annotations

"""
poster_generator.py

Image composition is UNCHANGED:
  - Template path, photo placement (x, y, w, h), corner radius
  - Font, font size, colour, name centering position
  - Output path format

What changed:
  - generate_poster() now accepts a member dict that may contain either:
      "photo"     → local filename inside PHOTO_FOLDER  (legacy Excel path)
      "photo_url" → public HTTPS URL from Supabase Storage (new Supabase path)
    Both produce identical poster output.
  - get_today_birthdays() is preserved for backward-compat but is no longer
    called by app.py.  The app now uses core.db.get_today_birthdays() instead.
"""

from datetime import date, datetime
from io import BytesIO
from pathlib import Path
from typing import Any
import zipfile

import pandas as pd
import requests as _requests
from PIL import Image, ImageDraw, ImageFont

import config


# ── Photo loading ─────────────────────────────────────────────────────────────

def _load_photo(member: dict[str, str]) -> Image.Image:
    """
    Load the member photo from either:
      1. photo_url  — public HTTPS URL (Supabase Storage)
      2. photo      — local filename inside config.PHOTO_FOLDER  (legacy)
    """
    photo_url: str | None = member.get("photo_url") or ""
    photo_local: str | None = member.get("photo") or ""

    if photo_url and photo_url.startswith("http"):
        resp = _requests.get(photo_url, timeout=20)
        resp.raise_for_status()
        return Image.open(BytesIO(resp.content))

    if photo_local:
        path = config.PHOTO_FOLDER / Path(photo_local).name
        return Image.open(path)

    raise ValueError(
        f"Member '{member.get('name')}' has no photo_url or local photo to load."
    )


# ── Image helpers (UNCHANGED) ─────────────────────────────────────────────────

def _resize_image(image: Image.Image, size: tuple[int, int]) -> Image.Image:
    resampling = getattr(Image, "Resampling", Image)
    return image.resize(size, resampling.LANCZOS)


def _apply_rounded_corners(image: Image.Image, radius: int) -> Image.Image:
    rounded_image = image.convert("RGBA")
    mask = Image.new("L", rounded_image.size, 0)
    draw = ImageDraw.Draw(mask)
    draw.rounded_rectangle(
        (0, 0, rounded_image.width, rounded_image.height),
        radius=radius,
        fill=255,
    )
    rounded_image.putalpha(mask)
    return rounded_image


def _member_output_path(member: dict[str, str]) -> Path:
    member_name = str(member["name"]).strip()
    if not member_name:
        raise ValueError("Member name is required to generate a poster")
    return config.OUTPUT_FOLDER / f"{date.today():%Y-%m-%d}_{member_name}.png"


# ── Template resolution ───────────────────────────────────────────────────────

def _get_template_path() -> Path:
    """
    Return the poster template to use.
    If a default template URL is stored in Supabase, download it to a temp file.
    Falls back to config.TEMPLATE_PATH (local file) in all error cases.
    """
    try:
        from core.db import get_default_template
        tpl = get_default_template()
        if tpl and tpl.get("public_url"):
            resp = _requests.get(tpl["public_url"], timeout=20)
            resp.raise_for_status()
            # Write to a predictable temp path so we reuse it within the same process
            tmp = config.OUTPUT_FOLDER / "_active_template.png"
            config.OUTPUT_FOLDER.mkdir(parents=True, exist_ok=True)
            tmp.write_bytes(resp.content)
            return tmp
    except Exception:
        pass
    return config.TEMPLATE_PATH


# ── Public API ────────────────────────────────────────────────────────────────

def generate_poster(member: dict[str, str]) -> Path:
    """
    Compose and save a birthday poster for `member`.

    member must contain:
      "name"      — display name (required)
      "photo_url" — Supabase public URL   (preferred)
      OR
      "photo"     — local filename in PHOTO_FOLDER  (legacy)

    Returns the Path of the saved PNG.
    Algorithm (coordinates, font, colours) is UNCHANGED.
    """
    config.OUTPUT_FOLDER.mkdir(parents=True, exist_ok=True)

    template_path = _get_template_path()
    template = Image.open(template_path).convert("RGBA")

    photo = _load_photo(member)
    photo = _resize_image(photo, (config.PHOTO_WIDTH, config.PHOTO_HEIGHT))
    photo = _apply_rounded_corners(photo, config.PHOTO_CORNER_RADIUS)
    template.paste(photo, (config.PHOTO_X, config.PHOTO_Y), photo)

    draw = ImageDraw.Draw(template)
    font = ImageFont.truetype(str(config.FONT_PATH), config.FONT_SIZE)
    name = str(member["name"]).strip()
    bbox = draw.textbbox((0, 0), name, font=font)
    text_width = bbox[2] - bbox[0]
    x_position = config.NAME_CENTER_X - (text_width / 2) - bbox[0]
    y_position = config.NAME_Y - bbox[1]
    draw.text((x_position, y_position), name, font=font, fill=config.FONT_COLOR)

    output_path = _member_output_path(member)
    template.save(output_path)
    return output_path


# ── Legacy Excel path (kept for backward-compat, no longer called by app.py) ─

def _resolve_members_file(path: str | Path | None = None) -> Path:
    candidate = Path(path) if path is not None else config.EXCEL_PATH
    if candidate.exists():
        return candidate
    raise FileNotFoundError(f"Members file not found: {candidate}")


def _load_members_frame(path: str | Path | None = None) -> pd.DataFrame:
    members_file = _resolve_members_file(path)
    try:
        if members_file.suffix.lower() == ".xlsx":
            return pd.read_excel(members_file, engine="openpyxl")
        if members_file.suffix.lower() == ".xls":
            return pd.read_excel(members_file)
        return pd.read_excel(members_file)
    except (ValueError, zipfile.BadZipFile, OSError):
        return pd.read_csv(members_file, sep=r"\t+|\s{2,}", engine="python")


def _birthday_matches_today(birthday_value: Any, today: date) -> bool:
    if pd.isna(birthday_value):
        return False
    if isinstance(birthday_value, pd.Timestamp):
        birthday_date = birthday_value.to_pydatetime().date()
        return birthday_date.month == today.month and birthday_date.day == today.day
    if isinstance(birthday_value, datetime):
        return birthday_value.month == today.month and birthday_value.day == today.day
    if isinstance(birthday_value, date):
        return birthday_value.month == today.month and birthday_value.day == today.day
    birthday_text = str(birthday_value).strip()
    parsed_birthday = pd.to_datetime(birthday_text, errors="coerce", dayfirst=True)
    if not pd.isna(parsed_birthday):
        return parsed_birthday.month == today.month and parsed_birthday.day == today.day
    for birthday_format in ("%d-%b", "%d-%b-%Y", "%d/%b", "%d/%b/%Y", "%d-%m", "%d/%m"):
        try:
            birthday_date = datetime.strptime(birthday_text, birthday_format).date()
        except ValueError:
            continue
        return birthday_date.month == today.month and birthday_date.day == today.day
    return False


def get_today_birthdays(
    path: str | Path | None = None,
    today: date | None = None,
) -> list[dict[str, str]]:
    """Legacy Excel-based birthday detection. Preserved for backward-compat."""
    today = today or date.today()
    members_frame = _load_members_frame(path)
    missing_columns = [
        col for col in config.REQUIRED_COLUMNS if col not in members_frame.columns
    ]
    if missing_columns:
        raise ValueError(f"Missing required columns: {', '.join(missing_columns)}")
    birthdays: list[dict[str, str]] = []
    for _, row in members_frame.iterrows():
        if _birthday_matches_today(row["Birthday"], today):
            birthdays.append({
                "name":  "" if pd.isna(row["Name"])  else str(row["Name"]),
                "photo": "" if pd.isna(row["Photo"]) else str(row["Photo"]),
            })
    return birthdays
