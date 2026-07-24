-- ============================================================
-- Migration 003: app_settings, generation_history, activity_log
-- Run in Supabase Dashboard → SQL Editor
-- ============================================================

-- ── app_settings ─────────────────────────────────────────────
create table if not exists public.app_settings (
    key         text primary key,
    value       text not null,
    updated_at  timestamptz not null default now()
);

create or replace function public.set_app_settings_updated_at()
returns trigger language plpgsql as $$
begin new.updated_at = now(); return new; end; $$;

drop trigger if exists trg_app_settings_updated_at on public.app_settings;
create trigger trg_app_settings_updated_at
    before update on public.app_settings
    for each row execute function public.set_app_settings_updated_at();

alter table public.app_settings enable row level security;
drop policy if exists "svc_all_app_settings" on public.app_settings;
create policy "svc_all_app_settings" on public.app_settings
    for all using (true) with check (true);

-- Seed defaults (idempotent)
insert into public.app_settings (key, value) values
    ('app_name',        'Gradient Birthday Platform'),
    ('telegram_token',  ''),
    ('telegram_chat_id','')
on conflict (key) do nothing;

-- ── generation_history ───────────────────────────────────────
create table if not exists public.generation_history (
    id              uuid primary key default gen_random_uuid(),
    generated_at    timestamptz not null default now(),
    birthday_count  int not null default 0,
    member_names    text[] not null default '{}',
    status          text not null default 'success'
);

alter table public.generation_history enable row level security;
drop policy if exists "svc_all_generation_history" on public.generation_history;
create policy "svc_all_generation_history" on public.generation_history
    for all using (true) with check (true);

-- ── activity_log ─────────────────────────────────────────────
create table if not exists public.activity_log (
    id          uuid primary key default gen_random_uuid(),
    event_type  text not null,   -- member_added | member_updated | member_deleted | posters_generated
    description text not null,
    created_at  timestamptz not null default now()
);

alter table public.activity_log enable row level security;
drop policy if exists "svc_all_activity_log" on public.activity_log;
create policy "svc_all_activity_log" on public.activity_log
    for all using (true) with check (true);

-- ── poster_templates (metadata only; files live in Storage) ──
create table if not exists public.poster_templates (
    id          uuid primary key default gen_random_uuid(),
    name        text not null,
    storage_path text not null unique,
    public_url  text not null,
    is_default  boolean not null default false,
    created_at  timestamptz not null default now()
);

alter table public.poster_templates enable row level security;
drop policy if exists "svc_all_poster_templates" on public.poster_templates;
create policy "svc_all_poster_templates" on public.poster_templates
    for all using (true) with check (true);
