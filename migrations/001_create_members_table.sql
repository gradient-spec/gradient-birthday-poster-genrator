-- ============================================================
-- Migration: 001_create_members_table
-- Run once in Supabase Dashboard → SQL Editor
-- ============================================================

-- NOTE: table already existed with column name "is_Active" (capital A).
-- The app uses "is_Active" everywhere to match the existing schema.
create table if not exists public.members (
    id          uuid primary key default gen_random_uuid(),
    name        text not null,
    birth_date  date not null,
    photo_url   text,
    "is_Active" boolean not null default true,
    created_at  timestamptz not null default now(),
    updated_at  timestamptz not null default now()
);

-- Auto-update updated_at on every row change
create or replace function public.set_updated_at()
returns trigger language plpgsql as $$
begin
    new.updated_at = now();
    return new;
end;
$$;

drop trigger if exists trg_members_updated_at on public.members;
create trigger trg_members_updated_at
    before update on public.members
    for each row execute function public.set_updated_at();

-- Row Level Security: service role (used by anon key in this app) can do all
alter table public.members enable row level security;

drop policy if exists "allow_all_authenticated" on public.members;
create policy "allow_all_authenticated"
    on public.members
    for all
    using (true)
    with check (true);
