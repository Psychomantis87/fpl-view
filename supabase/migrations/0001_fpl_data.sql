-- One row per data type ("players", "fixtures"), each holding the whole
-- payload as jsonb. The Edge Function overwrites these on every cron run;
-- the frontend just reads them.
create table if not exists public.fpl_data (
  key text primary key,
  payload jsonb not null,
  updated_at timestamptz not null default now()
);

alter table public.fpl_data enable row level security;

-- Public, read-only. Nobody but the Edge Function (using the service_role
-- key, which bypasses RLS entirely) can write.
create policy "Public read access"
  on public.fpl_data
  for select
  to anon, authenticated
  using (true);
