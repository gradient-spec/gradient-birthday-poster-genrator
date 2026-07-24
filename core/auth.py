from __future__ import annotations

from functools import wraps
from typing import Callable

from flask import Blueprint, redirect, render_template, request, session, url_for
from supabase_auth.errors import AuthApiError

from core.supabase_client import supabase

auth_bp = Blueprint("auth", __name__)

# ── Session key used to persist the logged-in user ──────────────────────────
_SESSION_KEY = "user_email"


# ── Decorator ────────────────────────────────────────────────────────────────

def login_required(view: Callable) -> Callable:
    """Redirect unauthenticated requests to /login."""

    @wraps(view)
    def wrapper(*args, **kwargs):
        if not session.get(_SESSION_KEY):
            return redirect(url_for("auth.login"))
        return view(*args, **kwargs)

    return wrapper


# ── Routes ───────────────────────────────────────────────────────────────────

@auth_bp.get("/login")
def login():
    if session.get(_SESSION_KEY):
        return redirect(url_for("home"))
    return render_template("login.html", error=None)


@auth_bp.post("/login")
def login_post():
    email = request.form.get("email", "").strip()
    password = request.form.get("password", "").strip()

    if not email or not password:
        return render_template("login.html", error="Email and password are required."), 400

    try:
        response = supabase.auth.sign_in_with_password({"email": email, "password": password})
        session[_SESSION_KEY] = response.user.email
        return redirect(url_for("home"))
    except AuthApiError as exc:
        return render_template("login.html", error="Invalid email or password."), 401
    except Exception as exc:
        return render_template("login.html", error=f"An unexpected error occurred: {exc}"), 500


@auth_bp.post("/logout")
def logout():
    session.clear()
    return redirect(url_for("auth.login"))
