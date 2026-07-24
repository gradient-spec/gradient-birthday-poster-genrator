from __future__ import annotations

from supabase import Client, create_client

from core.config import SUPABASE_ANON_KEY, SUPABASE_URL

# Supabase client using the anon key.
# This client is subject to Row Level Security policies.
#
# Use this ONLY for:
#   - Authentication operations (sign_in_with_password, sign_out, etc.)
#
# For database and storage operations, use core.supabase_admin.supabase_admin instead.
supabase: Client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
