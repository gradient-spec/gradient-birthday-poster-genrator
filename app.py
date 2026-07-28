from __future__ import annotations

from datetime import date
from pathlib import Path

from flask import Flask, jsonify, render_template, request, session

from core.auth import auth_bp, login_required
from core.config import SECRET_KEY
from core.db import (
    get_active_member_count,
    get_all_settings,
    get_last_generation,
    get_today_birthdays,
    get_upcoming_birthdays,
    list_activity,
    list_history,
    list_templates,
    log_activity,
    record_generation,
    rename_template,
    save_settings,
    set_default_template,
    delete_template,
    upload_template,
)
from core.members import (
    create_member,
    delete_member,
    list_members,
    update_member,
    upload_photo,
)
from poster_generator import generate_poster
from telegram_sender import send_posters_to_telegram
import config

app = Flask(__name__)
app.secret_key = SECRET_KEY

app.register_blueprint(auth_bp)


# ═══════════════════════════════════════════════════════════════════════════════
# HEALTH  (no auth, no DB — polled by the static Vercel loader to detect wake-up)
# ═══════════════════════════════════════════════════════════════════════════════

@app.get("/health")
def health():
    """Lightweight liveness probe. No DB, no auth, no logging.
    Returns CORS header so the static Vercel loader can poll from
    https://birthday.gradientclub.in without being blocked by the browser.
    """
    response = jsonify({"status": "ok"})
    response.headers["Access-Control-Allow-Origin"] = "https://birthday-posters.gradientclub.in"
    return response


# ── Shared template context ───────────────────────────────────────────────────

def _base_ctx(**extra) -> dict:
    return {
        "user":        session.get("user_email"),
        "today_date":  date.today().strftime("%A, %d %B %Y"),
        **extra,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# DASHBOARD
# ═══════════════════════════════════════════════════════════════════════════════

@app.get("/")
@login_required
def home():
    today_birthdays = get_today_birthdays()
    upcoming        = get_upcoming_birthdays(7)
    last_gen        = get_last_generation()
    activity        = list_activity(10)

    if last_gen:
        last_gen_str = last_gen["generated_at"][:10]
    else:
        last_gen_str = "Never"

    return render_template(
        "index.html",
        active_page="dashboard",
        today_count=len(today_birthdays),
        total_members=get_active_member_count(),
        upcoming=upcoming,
        last_generated=last_gen_str,
        activity=activity,
        message=None,
        **_base_ctx(),
    )


@app.post("/generate")
@login_required
def generate_today_posters():
    today_birthdays = get_today_birthdays()
    poster_paths    = []
    birthday_names  = []
    error_msg       = None

    try:
        for member in today_birthdays:
            poster_paths.append(generate_poster(member))
            birthday_names.append(member["name"])

        if poster_paths:
            send_posters_to_telegram(poster_paths, birthday_names)
            message = (
                f"Successfully generated and sent "
                f"{len(poster_paths)} poster(s) to Telegram."
            )
            record_generation(len(poster_paths), birthday_names, "success")
            log_activity(
                "posters_generated",
                f"Generated {len(poster_paths)} poster(s): {', '.join(birthday_names)}",
            )
        else:
            message = "No birthdays found today. No posters were generated."
            record_generation(0, [], "no_birthdays")

    except Exception as exc:
        error_msg = str(exc)
        record_generation(len(birthday_names), birthday_names, "error")
        message = f"Failed to generate posters: {exc}"

    upcoming = get_upcoming_birthdays(7)
    last_gen = get_last_generation()
    last_gen_str = last_gen["generated_at"][:10] if last_gen else "Never"

    status = 500 if error_msg else 200
    return render_template(
        "index.html",
        active_page="dashboard",
        today_count=len(today_birthdays),
        total_members=get_active_member_count(),
        upcoming=upcoming,
        last_generated=last_gen_str,
        activity=list_activity(10),
        message=message,
        **_base_ctx(),
    ), status


# ═══════════════════════════════════════════════════════════════════════════════
# MEMBERS PAGE + API
# ═══════════════════════════════════════════════════════════════════════════════

@app.get("/members")
@login_required
def members():
    return render_template(
        "members.html",
        active_page="members",
        **_base_ctx(),
    )


@app.get("/api/members")
@login_required
def api_members_list():
    try:
        rows = list_members()
        return jsonify({"ok": True, "members": rows})
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500


@app.post("/api/members")
@login_required
def api_members_create():
    try:
        name       = (request.form.get("name") or "").strip()
        birth_date = (request.form.get("birth_date") or "").strip()
        is_active  = request.form.get("is_active", "true").lower() == "true"
        if not name:
            return jsonify({"ok": False, "error": "Name is required."}), 400
        if not birth_date:
            return jsonify({"ok": False, "error": "Birthday is required."}), 400

        photo_url  = None
        photo_file = request.files.get("photo")
        if photo_file and photo_file.filename:
            photo_url = upload_photo(photo_file.read(), photo_file.mimetype or "image/jpeg")

        row = create_member(name, birth_date, photo_url, is_active)
        log_activity("member_added", f"Added member: {name}")
        return jsonify({"ok": True, "member": row}), 201
    except ValueError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500


@app.put("/api/members/<member_id>")
@login_required
def api_members_update(member_id: str):
    try:
        name       = (request.form.get("name") or "").strip()
        birth_date = (request.form.get("birth_date") or "").strip()
        is_active  = request.form.get("is_active", "true").lower() == "true"
        if not name:
            return jsonify({"ok": False, "error": "Name is required."}), 400
        if not birth_date:
            return jsonify({"ok": False, "error": "Birthday is required."}), 400

        photo_url  = None
        photo_file = request.files.get("photo")
        if photo_file and photo_file.filename:
            photo_url = upload_photo(photo_file.read(), photo_file.mimetype or "image/jpeg")

        row = update_member(member_id, name, birth_date, photo_url, is_active)
        log_activity("member_updated", f"Updated member: {name}")
        return jsonify({"ok": True, "member": row})
    except ValueError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500


@app.delete("/api/members/<member_id>")
@login_required
def api_members_delete(member_id: str):
    try:
        from core.members import get_member
        m = get_member(member_id)
        name = m["name"] if m else member_id
        delete_member(member_id)
        log_activity("member_deleted", f"Deleted member: {name}")
        return jsonify({"ok": True})
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500


# ═══════════════════════════════════════════════════════════════════════════════
# HISTORY
# ═══════════════════════════════════════════════════════════════════════════════

@app.get("/history")
@login_required
def history():
    rows = list_history(100)
    return render_template(
        "history.html",
        active_page="history",
        history=rows,
        **_base_ctx(),
    )


# ═══════════════════════════════════════════════════════════════════════════════
# SETTINGS
# ═══════════════════════════════════════════════════════════════════════════════

@app.get("/settings")
@login_required
def settings():
    current = get_all_settings()
    return render_template(
        "settings.html",
        active_page="settings",
        settings=current,
        saved=False,
        **_base_ctx(),
    )


@app.post("/settings")
@login_required
def settings_save():
    new_settings = {
        "app_name":         (request.form.get("app_name") or "").strip(),
        "telegram_token":   (request.form.get("telegram_token") or "").strip(),
        "telegram_chat_id": (request.form.get("telegram_chat_id") or "").strip(),
    }
    error = None
    try:
        save_settings(new_settings)
        # Live-patch the runtime config so Telegram works immediately
        if new_settings["telegram_token"]:
            config.BOT_TOKEN = new_settings["telegram_token"]
        if new_settings["telegram_chat_id"]:
            config.CHAT_ID = new_settings["telegram_chat_id"]
        log_activity("settings_updated", "Application settings updated")
    except Exception as exc:
        error = str(exc)

    current = get_all_settings()
    return render_template(
        "settings.html",
        active_page="settings",
        settings=current,
        saved=(error is None),
        error=error,
        **_base_ctx(),
    )


# ═══════════════════════════════════════════════════════════════════════════════
# TEMPLATES
# ═══════════════════════════════════════════════════════════════════════════════

@app.get("/templates")
@login_required
def templates_page():
    return render_template(
        "templates_page.html",
        active_page="templates",
        **_base_ctx(),
    )


@app.get("/api/templates")
@login_required
def api_templates_list():
    try:
        return jsonify({"ok": True, "templates": list_templates()})
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500


@app.post("/api/templates")
@login_required
def api_templates_upload():
    try:
        f    = request.files.get("template")
        name = (request.form.get("name") or "").strip()
        if not f or not f.filename:
            return jsonify({"ok": False, "error": "No file provided."}), 400
        if not name:
            name = Path(f.filename).stem
        row = upload_template(f.read(), f.mimetype or "image/png", name)
        log_activity("template_uploaded", f"Uploaded template: {name}")
        return jsonify({"ok": True, "template": row}), 201
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500


@app.patch("/api/templates/<template_id>/rename")
@login_required
def api_templates_rename(template_id: str):
    try:
        new_name = (request.json or {}).get("name", "").strip()
        if not new_name:
            return jsonify({"ok": False, "error": "Name is required."}), 400
        row = rename_template(template_id, new_name)
        return jsonify({"ok": True, "template": row})
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500


@app.patch("/api/templates/<template_id>/set-default")
@login_required
def api_templates_set_default(template_id: str):
    try:
        set_default_template(template_id)
        log_activity("template_default_changed", f"Changed default template to ID {template_id}")
        return jsonify({"ok": True})
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500


@app.delete("/api/templates/<template_id>")
@login_required
def api_templates_delete(template_id: str):
    try:
        delete_template(template_id)
        log_activity("template_deleted", f"Deleted template ID {template_id}")
        return jsonify({"ok": True})
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500


# ═══════════════════════════════════════════════════════════════════════════════
# BOOT
# ═══════════════════════════════════════════════════════════════════════════════

def _sync_settings_to_config() -> None:
    """On startup, pull Telegram credentials from Supabase into runtime config."""
    try:
        token   = get_all_settings().get("telegram_token", "")
        chat_id = get_all_settings().get("telegram_chat_id", "")
        if token:
            config.BOT_TOKEN = token
        if chat_id:
            config.CHAT_ID = chat_id
    except Exception:
        pass


_sync_settings_to_config()


if __name__ == "__main__":
    app.run(debug=True)
