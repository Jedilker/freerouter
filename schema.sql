create extension if not exists pgcrypto;

create table if not exists public.user_api_keys (
    id bigint generated always as identity primary key,
    user_id uuid not null references auth.users (id) on delete cascade,
    key_hash text not null,
    key_prefix text not null,
    is_active boolean not null default true,
    created_at timestamptz not null default now()
);

-- Add the new fields when upgrading the original plaintext-key table.
alter table public.user_api_keys
    add column if not exists key_hash text,
    add column if not exists key_prefix text,
    add column if not exists is_active boolean not null default true,
    add column if not exists created_at timestamptz not null default now();

do $$
begin
    if exists (
        select 1
        from information_schema.columns
        where table_schema = 'public'
          and table_name = 'user_api_keys'
          and column_name = 'api_key'
    ) then
        update public.user_api_keys
        set key_hash = encode(digest(convert_to(api_key, 'UTF8'), 'sha256'), 'hex'),
            key_prefix = left(api_key, 16)
        where key_hash is null and api_key is not null;

        -- Remove legacy plaintext credentials after hashing them in place.
        alter table public.user_api_keys drop column api_key;
    end if;
end $$;

alter table public.user_api_keys alter column key_hash set not null;
alter table public.user_api_keys alter column key_prefix set not null;
create unique index if not exists user_api_keys_key_hash_uidx
    on public.user_api_keys (key_hash);
create index if not exists user_api_keys_user_id_idx
    on public.user_api_keys (user_id);

create table if not exists public.router_logs (
    id bigint generated always as identity primary key,
    user_id uuid not null references auth.users (id) on delete cascade,
    target_model text not null,
    routing_reason text not null,
    latency_ms double precision not null check (latency_ms >= 0),
    created_at timestamptz not null default now()
);

-- Older logs had no owner and stored prompt text. Keep unowned rows inaccessible
-- to analytics and discard their sensitive prompt content during this migration.
alter table public.router_logs
    add column if not exists id bigint generated always as identity,
    add column if not exists user_id uuid references auth.users (id) on delete cascade,
    add column if not exists target_model text,
    add column if not exists routing_reason text,
    add column if not exists latency_ms double precision,
    add column if not exists created_at timestamptz not null default now();
alter table public.router_logs drop column if exists prompt;

create index if not exists router_logs_user_created_at_idx
    on public.router_logs (user_id, created_at desc);

alter table public.user_api_keys enable row level security;
alter table public.router_logs enable row level security;

-- The API accesses these tables only from the server using the service-role key.
-- Do not add public/anon policies for API keys or routing history.
