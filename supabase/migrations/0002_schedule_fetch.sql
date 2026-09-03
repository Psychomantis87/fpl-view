-- Fallback / reference only - the recommended way to schedule this is
-- Supabase Dashboard > Database > Cron Jobs, which stores the URL/key in
-- Vault (vault.decrypted_secrets) instead of plaintext SQL like this file
-- does. See README Step 4. If you use this file instead, run it manually in
-- the SQL Editor (not via `supabase db push`) after filling in your project
-- ref and key below. Requires the pg_cron and pg_net extensions enabled
-- first (Database > Extensions).
--
-- The Authorization header just needs to be a valid Supabase API key to get
-- past the Edge Function gateway - the function itself already has its own
-- service_role access via its auto-injected environment for the actual
-- privileged database write. Use your publishable/anon key here, not
-- service_role: it's safe to expose even if this job definition is ever
-- visible to someone, unlike service_role.

select cron.schedule(
  'fetch-fpl-data-every-10min',
  '*/10 * * * *',  -- fixed marks - :00, :10, :20, :30, :40, :50; use '0 * * * *' for hourly instead
  $$
  select net.http_post(
    url := 'https://hfltmwfghoxgaelzsxnl.supabase.co/functions/v1/fetch-fpl-data',
    headers := jsonb_build_object(
      'Content-Type', 'application/json',
      'Authorization', 'Bearer sb_publishable_FT6S_zfe-mU4hTc49HcIdA_olRWZPyh'
    )
  );
  $$
);

-- To check it's registered:
--   select * from cron.job;
-- To see run history:
--   select * from cron.job_run_details order by start_time desc limit 10;
-- To change an existing job's schedule without recreating it:
--   select cron.alter_job(job_id := <id from cron.job>, schedule := '*/10 * * * *');
-- To remove it:
--   select cron.unschedule('fetch-fpl-data-every-10min');
