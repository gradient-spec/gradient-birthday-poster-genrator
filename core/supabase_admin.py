from __future__ import annotations

from supabase import Client, create_client

from core.config import SUPABASE_SERVICE_ROLE_KEY, SUPABASE_URL

# Admin client using the service role key.
# This client bypasses Row Level Security and should ONLY be used for
# server-side operations in a trusted Flask backend.
#
# Use this for:
#   - Database CRUD operations (members table)
#   - Storage operations (upload, delete)
#
# Do NOT use this for authentication — use core.supabase_client.supabase instead.
supabase_admin: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
