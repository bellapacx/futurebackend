-- ============================================================
-- 1. PROFILES
-- ============================================================
create table public.profiles (
  id uuid primary key references auth.users(id) on delete cascade,
  email text,
  display_name text,
  avatar_url text,
  auth_provider text check (auth_provider in ('google', 'email')),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

alter table public.profiles enable row level security;

create policy "Users can read own profile"
  on public.profiles for select
  using (auth.uid() = id);

create policy "Users can update own profile"
  on public.profiles for update
  using (auth.uid() = id);

create or replace function public.handle_new_user()
returns trigger
language plpgsql
security definer set search_path = public
as $$
begin
  insert into public.profiles (id, email, display_name, avatar_url, auth_provider)
  values (
    new.id,
    new.email,
    coalesce(new.raw_user_meta_data->>'full_name', new.raw_user_meta_data->>'name'),
    new.raw_user_meta_data->>'avatar_url',
    case
      when new.raw_app_meta_data->>'provider' = 'google' then 'google'
      else 'email'
    end
  )
  on conflict (id) do nothing;
  return new;
end;
$$;

create trigger on_auth_user_created
  after insert on auth.users
  for each row execute function public.handle_new_user();

-- ============================================================
-- 2. WHOP MEMBERSHIPS
-- ============================================================
create table public.whop_memberships (
  id uuid primary key default gen_random_uuid(),
  whop_membership_id text unique not null,
  whop_user_id text,
  whop_plan_id text,
  status text not null check (status in ('active','trialing','past_due','canceled','expired','inactive')),
  current_period_start timestamptz,
  current_period_end timestamptz,
  cancel_at_period_end boolean not null default false,
  raw_payload jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index idx_whop_memberships_status on public.whop_memberships(status);
create index idx_whop_memberships_period_end on public.whop_memberships(current_period_end);

alter table public.whop_memberships enable row level security;

-- ============================================================
-- 3. USER ENTITLEMENTS
-- ============================================================
create table public.user_entitlements (
  user_id uuid primary key references auth.users(id) on delete cascade,
  membership_id uuid references public.whop_memberships(id) on delete set null,
  is_active boolean not null default false,
  plan_tier text,
  expires_at timestamptz,
  last_verified_at timestamptz,
  updated_at timestamptz not null default now()
);

create index idx_user_entitlements_active on public.user_entitlements(is_active);
create index idx_user_entitlements_expires on public.user_entitlements(expires_at);

alter table public.user_entitlements enable row level security;

create policy "Users can read own entitlement"
  on public.user_entitlements for select
  using (auth.uid() = user_id);

-- ============================================================
-- 4. WHOP WEBHOOK EVENTS (idempotency)
-- ============================================================
create table public.whop_webhook_events (
  id uuid primary key default gen_random_uuid(),
  whop_event_id text unique not null,
  event_type text not null,
  payload jsonb not null,
  signature_valid boolean not null,
  processed_at timestamptz,
  processing_error text,
  received_at timestamptz not null default now()
);

alter table public.whop_webhook_events enable row level security;

-- ============================================================
-- 5. INDICATOR VERSIONS
-- ============================================================
create table public.indicator_versions (
  id uuid primary key default gen_random_uuid(),
  version_label text unique not null,
  pine_source_encrypted bytea not null,
  source_hash text not null,
  status text not null default 'draft'
    check (status in ('draft','validated','active','archived','rolled_back')),
  validation_report jsonb,
  validated_at timestamptz,
  activated_at timestamptz,
  activated_by uuid references auth.users(id),
  created_at timestamptz not null default now(),
  created_by uuid references auth.users(id),
  notes text
);

create unique index one_active_indicator
  on public.indicator_versions ((status))
  where status = 'active';

alter table public.indicator_versions enable row level security;

-- ============================================================
-- 6. CHART LAYOUTS
-- ============================================================
create table public.chart_layouts (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  name text not null,
  symbol text not null default 'NQ',
  timeframe text not null default '1m',
  layout_config jsonb not null default '{}'::jsonb,
  is_default boolean not null default false,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index idx_chart_layouts_user on public.chart_layouts(user_id);

alter table public.chart_layouts enable row level security;

create policy "Users manage own layouts"
  on public.chart_layouts for all
  using (auth.uid() = user_id)
  with check (auth.uid() = user_id);

-- ============================================================
-- 7. USER PREFERENCES
-- ============================================================
create table public.user_preferences (
  user_id uuid primary key references auth.users(id) on delete cascade,
  theme text not null default 'dark',
  default_symbol text not null default 'NQ',
  default_timeframe text not null default '1m',
  preferences jsonb not null default '{}'::jsonb,
  updated_at timestamptz not null default now()
);

alter table public.user_preferences enable row level security;

create policy "Users manage own preferences"
  on public.user_preferences for all
  using (auth.uid() = user_id)
  with check (auth.uid() = user_id);

-- ============================================================
-- 8. ADMIN USERS
-- ============================================================
create table public.admin_users (
  user_id uuid primary key references auth.users(id) on delete cascade,
  role text not null default 'admin' check (role in ('owner','admin','viewer')),
  created_at timestamptz not null default now()
);

alter table public.admin_users enable row level security;

-- ============================================================
-- 9. AUDIT LOG
-- ============================================================
create table public.audit_log (
  id bigserial primary key,
  actor_user_id uuid references auth.users(id),
  action text not null,
  target_type text,
  target_id text,
  metadata jsonb,
  created_at timestamptz not null default now()
);

alter table public.audit_log enable row level security;