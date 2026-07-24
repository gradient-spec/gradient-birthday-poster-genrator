from __future__ import annotations

import uuid
from typing import Any

from core.supabase_admin import supabase_admin

# ── Constants ────────────────────────────────────────────────────────────────

TABLE = "members"
BUCKET = "member-photos"
ALLOWED_MIME = {"image/png", "image/jpeg", "image/webp"}
MAX_BYTES = 5 * 1024 * 1024  # 5 MB

# NOTE: The Supabase table uses "is_active" (lowercase).
_IS_ACTIVE_COL = "is_active"

SELECT_COLS = f"id, name, birth_date, photo_url, {_IS_ACTIVE_COL}, created_at, updated_at"


# ── Photo helpers ─────────────────────────────────────────────────────────────

def _ext_from_mime(mime: str) -> str:
    return {
        "image/png":  ".png",
        "image/jpeg": ".jpg",
        "image/webp": ".webp",
    }.get(mime, ".jpg")


def upload_photo(file_bytes: bytes, mime_type: str) -> str:
    """
    Upload a photo to the member-photos bucket.
    Returns the public URL of the uploaded file.
    Raises ValueError for invalid type / size.
    """
    if mime_type in ("image/jpg", "image/JPG"):
        mime_type = "image/jpeg"

    if mime_type not in ALLOWED_MIME:
        raise ValueError(
            f"Unsupported file type '{mime_type}'. Allowed: png, jpg, jpeg, webp."
        )

    if len(file_bytes) > MAX_BYTES:
        raise ValueError("File exceeds the 5 MB limit.")

    ext = _ext_from_mime(mime_type)
    filename = f"{uuid.uuid4().hex}{ext}"

    supabase_admin.storage.from_(BUCKET).upload(
        path=filename,
        file=file_bytes,
        file_options={"content-type": mime_type, "upsert": "false"},
    )

    return supabase_admin.storage.from_(BUCKET).get_public_url(filename)


def delete_photo(photo_url: str) -> None:
    """
    Remove a photo from the bucket given its public URL.
    Silently ignores errors (file may have been deleted already).
    """
    if not photo_url:
        return
    try:
        filename = photo_url.split(f"/{BUCKET}/")[-1].split("?")[0]
        supabase_admin.storage.from_(BUCKET).remove([filename])
    except Exception:
        pass


# ── CRUD helpers ──────────────────────────────────────────────────────────────

def list_members() -> list[dict[str, Any]]:
    """Return all members ordered by name."""
    resp = (
        supabase_admin.table(TABLE)
        .select(SELECT_COLS)
        .order("name")
        .execute()
    )
    return resp.data or []


def get_member(member_id: str) -> dict[str, Any] | None:
    """Return a single member by UUID, or None if not found."""
    resp = (
        supabase_admin.table(TABLE)
        .select(SELECT_COLS)
        .eq("id", member_id)
        .maybe_single()
        .execute()
    )
    return resp.data


def create_member(
    name: str,
    birth_date: str,
    photo_url: str | None,
    is_active: bool,
) -> dict[str, Any]:
    """
    Insert a new member row.
    birth_date must be ISO-8601 (YYYY-MM-DD).
    Returns the created row.
    """
    payload: dict[str, Any] = {
        "name":         name.strip(),
        "birth_date":   birth_date,
        "photo_url":    photo_url or None,
        _IS_ACTIVE_COL: is_active,
    }
    resp = supabase_admin.table(TABLE).insert(payload).execute()
    if not resp.data:
        raise RuntimeError("Insert returned no data.")
    return resp.data[0]


def update_member(
    member_id: str,
    name: str,
    birth_date: str,
    photo_url: str | None,
    is_active: bool,
) -> dict[str, Any]:
    """
    Update an existing member row.
    photo_url is only overwritten when a new value is explicitly supplied.
    Returns the updated row.
    """
    payload: dict[str, Any] = {
        "name":         name.strip(),
        "birth_date":   birth_date,
        _IS_ACTIVE_COL: is_active,
    }
    if photo_url is not None:
        payload["photo_url"] = photo_url

    resp = (
        supabase_admin.table(TABLE)
        .update(payload)
        .eq("id", member_id)
        .execute()
    )
    if not resp.data:
        raise RuntimeError("Update returned no data — member may not exist.")
    return resp.data[0]


def delete_member(member_id: str) -> None:
    """
    Delete a member row and remove their photo from storage.
    """
    member = get_member(member_id)
    if member and member.get("photo_url"):
        delete_photo(member["photo_url"])

    supabase_admin.table(TABLE).delete().eq("id", member_id).execute()
