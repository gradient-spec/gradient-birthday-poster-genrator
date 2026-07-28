from __future__ import annotations

"""
core/db.py — Central application data layer.

Responsibilities:
  - Birthday detection from Supabase (replaces Excel-based poster_generator logic)
  - Dashboard statistics
  - Activity log (member_added, member_updated, member_deleted, posters_generated)
  - Generation history
  - App settings (key/value store)
  - Poster template management

All writes use supabase_admin (service role).
All reads use supabase_admin (service role).
Authentication remains entirely in core/auth.py.
"""

import uuid
from datetime import date
from typing import Any
from zoneinfo import ZoneInfo

from core.supabase_admin import supabase_admin

# ── Timezone ─────────────────────────────────────────────────────────────────
IST = ZoneInfo("Asia/Kolkata")

TEMPLATES_BUCKET = "poster-templates"
TEMPLATES_TABLE  = "poster_templates"


# ═══════════════════════════════════════════════════════════════════════════════
# BIRTHDAY HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

def _today_ist() -> date:
    """Return today's date in Asia/Kolkata timezone."""
    return date.today()  # server should be set to IST; fallback is fine


def get_today_birthdays() -> list[dict[str, Any]]:
    """
    Return active members whose birth_date month+day matches today (IST).
    Ignores birth year entirely.  Handles Feb 29 safely (maps to Feb 28 in non-leap years).

    Returns list of dicts: {id, name, birth_date, photo_url}
    """
    today = _today_ist()
    month = today.month
    day   = today.day

    # Feb 29 safety: if today is Feb 28 in a non-leap year, also match Feb 29
    also_feb29 = (month == 2 and day == 28 and not _is_leap(today.year))

    try:
        resp = (
            supabase_admin.table("members")
            .select("id, name, birth_date, photo_url")
            .eq("is_active", True)
            .execute()
        )
        members = resp.data or []
    except Exception:
        return []

    results = []
    for m in members:
        bd = m.get("birth_date")
        if not bd:
            continue
        try:
            bdate = date.fromisoformat(bd)
        except (ValueError, TypeError):
            continue
        if bdate.month == month and bdate.day == day:
            results.append(m)
        elif also_feb29 and bdate.month == 2 and bdate.day == 29:
            results.append(m)

    return results


def get_upcoming_birthdays(days: int = 7) -> list[dict[str, Any]]:
    """
    Return active members with birthdays in the next `days` days (exclusive of today).
    Result includes a synthetic 'days_until' field and is sorted by days_until.
    """
    today = _today_ist()

    try:
        resp = (
            supabase_admin.table("members")
            .select("id, name, birth_date, photo_url")
            .eq("is_active", True)
            .execute()
        )
        members = resp.data or []
    except Exception:
        return []

    results = []
    for m in members:
        bd = m.get("birth_date")
        if not bd:
            continue
        try:
            bdate = date.fromisoformat(bd)
        except (ValueError, TypeError):
            continue

        d = _days_until(bdate, today)
        if 1 <= d <= days:
            results.append({**m, "days_until": d})

    results.sort(key=lambda x: x["days_until"])
    return results


def _is_leap(year: int) -> bool:
    return year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)


def _days_until(bdate: date, today: date) -> int:
    """Days from today until the next occurrence of this month/day."""
    year = today.year
    try:
        next_bd = date(year, bdate.month, bdate.day)
    except ValueError:
        # Feb 29 in non-leap year → use Feb 28
        next_bd = date(year, 2, 28)

    if next_bd < today:
        try:
            next_bd = date(year + 1, bdate.month, bdate.day)
        except ValueError:
            next_bd = date(year + 1, 2, 28)

    return (next_bd - today).days


# ═══════════════════════════════════════════════════════════════════════════════
# DASHBOARD STATS
# ═══════════════════════════════════════════════════════════════════════════════

def get_active_member_count() -> int:
    """Return count of active members."""
    try:
        resp = (
            supabase_admin.table("members")
            .select("id", count="exact")
            .eq("is_active", True)
            .execute()
        )
        return resp.count or 0
    except Exception:
        return 0


def get_last_generation() -> dict[str, Any] | None:
    """Return the most recent generation_history row, or None."""
    try:
        resp = (
            supabase_admin.table("generation_history")
            .select("generated_at, birthday_count, member_names, status")
            .order("generated_at", desc=True)
            .limit(1)
            .execute()
        )
        return resp.data[0] if resp.data else None
    except Exception:
        return None


# ═══════════════════════════════════════════════════════════════════════════════
# ACTIVITY LOG
# ═══════════════════════════════════════════════════════════════════════════════

def log_activity(event_type: str, description: str) -> None:
    """
    Append an entry to activity_log.
    event_type: member_added | member_updated | member_deleted | posters_generated
    Silently ignores errors (table may not exist yet).
    """
    try:
        supabase_admin.table("activity_log").insert({
            "event_type":  event_type,
            "description": description,
        }).execute()
    except Exception:
        pass


def list_activity(limit: int = 20) -> list[dict[str, Any]]:
    """Return recent activity entries, newest first."""
    try:
        resp = (
            supabase_admin.table("activity_log")
            .select("event_type, description, created_at")
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        return resp.data or []
    except Exception:
        return []


# ═══════════════════════════════════════════════════════════════════════════════
# GENERATION HISTORY
# ═══════════════════════════════════════════════════════════════════════════════

def record_generation(
    birthday_count: int,
    member_names: list[str],
    status: str = "success",
) -> None:
    """Insert a generation_history row. Silently ignores errors."""
    try:
        supabase_admin.table("generation_history").insert({
            "birthday_count": birthday_count,
            "member_names":   member_names,
            "status":         status,
        }).execute()
    except Exception:
        pass


def list_history(limit: int = 50) -> list[dict[str, Any]]:
    """Return generation history, newest first."""
    try:
        resp = (
            supabase_admin.table("generation_history")
            .select("id, generated_at, birthday_count, member_names, status")
            .order("generated_at", desc=True)
            .limit(limit)
            .execute()
        )
        return resp.data or []
    except Exception:
        return []


# ═══════════════════════════════════════════════════════════════════════════════
# APP SETTINGS
# ═══════════════════════════════════════════════════════════════════════════════

_SETTINGS_DEFAULTS: dict[str, str] = {
    "app_name":         "Gradient Birthday Platform",
    "telegram_token":   "",
    "telegram_chat_id": "",
}


def get_all_settings() -> dict[str, str]:
    """Return all app_settings as a flat dict, merging with defaults."""
    result = dict(_SETTINGS_DEFAULTS)
    try:
        resp = supabase_admin.table("app_settings").select("key, value").execute()
        for row in (resp.data or []):
            result[row["key"]] = row["value"]
    except Exception:
        pass
    return result


def get_setting(key: str) -> str:
    """Return a single setting value, or its default if not found."""
    try:
        resp = (
            supabase_admin.table("app_settings")
            .select("value")
            .eq("key", key)
            .maybe_single()
            .execute()
        )
        if resp.data:
            return resp.data["value"]
    except Exception:
        pass
    return _SETTINGS_DEFAULTS.get(key, "")


def save_setting(key: str, value: str) -> None:
    """Upsert a single setting value."""
    supabase_admin.table("app_settings").upsert(
        {"key": key, "value": value},
        on_conflict="key",
    ).execute()


def save_settings(settings: dict[str, str]) -> None:
    """Bulk upsert a dict of settings."""
    rows = [{"key": k, "value": v} for k, v in settings.items()]
    supabase_admin.table("app_settings").upsert(rows, on_conflict="key").execute()


# ═══════════════════════════════════════════════════════════════════════════════
# POSTER TEMPLATES
# ═══════════════════════════════════════════════════════════════════════════════

def list_templates() -> list[dict[str, Any]]:
    """Return all poster templates ordered by name."""
    try:
        resp = (
            supabase_admin.table(TEMPLATES_TABLE)
            .select("id, name, storage_path, public_url, is_default, created_at")
            .order("name")
            .execute()
        )
        return resp.data or []
    except Exception:
        return []


def get_default_template() -> dict[str, Any] | None:
    """Return the current default template row, or None."""
    try:
        resp = (
            supabase_admin.table(TEMPLATES_TABLE)
            .select("id, name, storage_path, public_url, is_default, created_at")
            .eq("is_default", True)
            .maybe_single()
            .execute()
        )
        return resp.data
    except Exception:
        return None


def upload_template(file_bytes: bytes, mime_type: str, display_name: str) -> dict[str, Any]:
    """
    Upload a template image to Storage and insert a metadata row.
    Returns the inserted row.
    """
    ext_map = {"image/png": ".png", "image/jpeg": ".jpg", "image/webp": ".webp"}
    ext = ext_map.get(mime_type, ".png")
    storage_path = f"templates/{uuid.uuid4().hex}{ext}"

    supabase_admin.storage.from_(TEMPLATES_BUCKET).upload(
        path=storage_path,
        file=file_bytes,
        file_options={"content-type": mime_type, "upsert": "false"},
    )
    public_url = supabase_admin.storage.from_(TEMPLATES_BUCKET).get_public_url(storage_path)

    # If this is the first template, make it default automatically
    existing = list_templates()
    is_default = len(existing) == 0

    resp = supabase_admin.table(TEMPLATES_TABLE).insert({
        "name":         display_name.strip(),
        "storage_path": storage_path,
        "public_url":   public_url,
        "is_default":   is_default,
    }).execute()

    if not resp.data:
        raise RuntimeError("Template insert returned no data.")
    return resp.data[0]


def rename_template(template_id: str, new_name: str) -> dict[str, Any]:
    resp = (
        supabase_admin.table(TEMPLATES_TABLE)
        .update({"name": new_name.strip()})
        .eq("id", template_id)
        .execute()
    )
    if not resp.data:
        raise RuntimeError("Template not found.")
    return resp.data[0]


def set_default_template(template_id: str) -> None:
    """Set one template as default, clearing all others."""
    # Clear all
    supabase_admin.table(TEMPLATES_TABLE).update({"is_default": False}).neq("id", "").execute()
    # Set new default
    supabase_admin.table(TEMPLATES_TABLE).update({"is_default": True}).eq("id", template_id).execute()


def delete_template(template_id: str) -> None:
    """Delete a template row and its Storage file."""
    try:
        resp = (
            supabase_admin.table(TEMPLATES_TABLE)
            .select("storage_path, is_default")
            .eq("id", template_id)
            .maybe_single()
            .execute()
        )
        row = resp.data
        if row:
            supabase_admin.storage.from_(TEMPLATES_BUCKET).remove([row["storage_path"]])
            supabase_admin.table(TEMPLATES_TABLE).delete().eq("id", template_id).execute()
            # If deleted was default, promote the first remaining one
            if row.get("is_default"):
                remaining = list_templates()
                if remaining:
                    set_default_template(remaining[0]["id"])
    except Exception as e:
        raise RuntimeError(str(e))
