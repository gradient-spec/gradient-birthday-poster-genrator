-- ============================================================
-- Migration: 002_rls_policy
-- Run in Supabase Dashboard → SQL Editor
--
-- This app uses the anon key from a server-side Flask app
-- (not from a browser), so granting anon full access is safe.
-- Access is controlled at the application layer via Flask auth.
-- ============================================================

-- Drop any existing restrictive policies
drop policy if exists "allow_all_authenticated" on public.members;
drop policy if exists "anon_select"             on public.members;
drop policy if exists "anon_insert"             on public.members;
drop policy if exists "anon_update"             on public.members;
drop policy if exists "anon_delete"             on public.members;

-- Allow the anon role (used by the Flask server via the anon key) full access
create policy "anon_select" on public.members
    for select to anon using (true);

create policy "anon_insert" on public.members
    for insert to anon with check (true);

create policy "anon_update" on public.members
    for update to anon using (true) with check (true);

create policy "anon_delete" on public.members
    for delete to anon using (true);
