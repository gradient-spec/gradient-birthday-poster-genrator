from __future__ import annotations

"""
poster_generator.py

Composes a birthday poster for a single member using PIL.

generate_poster(member) accepts a member dict containing:
  "name"      — display name (required)
  "photo_url" — public HTTPS URL from Supabase Storage (preferred)
  OR
  "photo"     — local filename inside config.PHOTO_FOLDER (fallback)

Returns the Path of the saved PNG.
"""

from datetime import date
from io import BytesIO
from pathlib import Path

import requests as _requests
from PIL import Image, ImageDraw, ImageFont

import config


# ── Photo loading ─────────────────────────────────────────────────────────────

def _load_photo(member: dict[str, str]) -> Image.Image:
    """
    Load the member photo from either:
      1. photo_url — public HTTPS URL (Supabase Storage)
      2. photo     — local filename inside config.PHOTO_FOLDER (fallback)
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


# ── Image helpers ─────────────────────────────────────────────────────────────

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
    Checks Supabase for a default template URL first; downloads it to a temp
    file so PIL can open it.  Falls back to config.TEMPLATE_PATH on any error.
    """
    try:
        from core.db import get_default_template
        tpl = get_default_template()
        if tpl and tpl.get("public_url"):
            resp = _requests.get(tpl["public_url"], timeout=20)
            resp.raise_for_status()
            # Cache to a predictable path so we reuse within the same process
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
    Returns the Path of the saved PNG.
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
