# FPL View — FPL data browser

A single-page dashboard for Fantasy Premier League data: every player stat the
`bootstrap-static` API exposes, upcoming fixture difficulty (FDR) per team,
club crests, filtering, sorting, saved views, and a Team View fixture ticker.

**Architecture**: static frontend (deployed to Vercel), fed by a Supabase
table that a scheduled Edge Function refreshes every 10 minutes. The page
itself never calls the FPL API directly — the browser can't (FPL's API sends
no CORS headers), so the Edge Function does it server-side instead and the
page just reads Supabase, which does allow browser access.

```
FPL API  --(cron, every 10 min)-->  Supabase Edge Function  -->  fpl_data table
                                                                        |
                                                              (public, read-only)
                                                                        |
                                                                        v
                                                     index.html on Vercel (reads it on load)
```

## Layout

```
index.html                    <- built page, this is what gets deployed (generated - don't hand-edit)
template.html                  <- real source: HTML/CSS/JS with __PLACEHOLDER__ slots
favicon.svg                    <- browser-tab icon, referenced by template.html's <link rel="icon">
supabase_config.json           <- your project's URL + anon key (gitignored - see Step 6)
supabase_config.example.json   <- template for the above, checked into git
data/
  players.json                  <- reference snapshot / seed data, not embedded in the page anymore
  team_fixtures.json            <- reference snapshot / seed data, not embedded in the page anymore
  team_logos.json                <- club crests, base64 - still embedded directly in index.html
scripts/
  fetch_players.py              <- local snapshot refresh (data/players.json) - optional now, Supabase does this
  fetch_fixtures.py             <- local snapshot refresh (data/team_fixtures.json) - optional now
  fetch_logos.py                <- refreshes data/team_logos.json (only needed if the league's teams change)
  build.py                       <- merges template.html + team_logos.json + supabase_config.json -> index.html
supabase/
  migrations/0001_fpl_data.sql   <- creates the fpl_data table + read-only RLS policy
  migrations/0002_schedule_fetch.sql  <- SQL fallback for the cron job (Dashboard > Cron Jobs is the recommended way - see Step 4)
  functions/fetch-fpl-data/index.ts    <- the Edge Function: fetches FPL, writes to fpl_data
```

---

## Step-by-step: wiring up Supabase

You said the existing `my-supabase-app` config is outdated — these steps work
whether that's the same Supabase *project* with fresh keys, or a brand new
project. Either way you need the Supabase CLI once:

```
npm install -g supabase
supabase login
```

### 1. Get (or confirm) a Supabase project
Open [supabase.com/dashboard](https://supabase.com/dashboard). Use the
existing project if it's still there, or **New project** for a fresh one.
Note its **Project Ref** (in the URL and in Settings → General) — you'll
need it below.

### 2. Create the table
Dashboard → **SQL Editor** → paste the contents of
`supabase/migrations/0001_fpl_data.sql` → Run.
This creates `public.fpl_data` (key, payload jsonb, updated_at) with a
read-only policy open to anyone holding the anon key — which is fine, the
anon key is meant to be public; the table only allows *reads* for it.

### 3. Deploy the Edge Function
From this folder:
```
supabase link --project-ref YOUR_PROJECT_REF
supabase functions deploy fetch-fpl-data
```
No secrets to set manually — `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY`
are injected into every Edge Function automatically.

**Seed it immediately** (don't wait for the first cron tick):
Dashboard → Edge Functions → `fetch-fpl-data` → **Invoke** (or
`supabase functions invoke fetch-fpl-data`). Check Settings → Database →
Table Editor → `fpl_data` — you should see 2 rows (`players`, `fixtures`).

### 4. Schedule it every 10 minutes
Dashboard → **Database → Extensions** → enable `pg_cron` and `pg_net` first.

**Recommended: Database → Cron Jobs** (Supabase's built-in scheduler UI).
Create a job named `fetch-fpl-data-every-10min`, schedule `*/10 * * * *`
(fixed marks - :00, :10, :20 …), type **HTTP Request**, method **POST**,
pointed at your Edge Function URL
(`https://YOUR_PROJECT_REF.supabase.co/functions/v1/fetch-fpl-data`), with
an `apikey` / `Authorization: Bearer <key>` header. The dashboard stores
whatever key you give it in **Vault** (`vault.decrypted_secrets`) rather
than in plaintext SQL - use your **publishable/anon** key here, not
service_role: the Edge Function already has its own service_role access
via its auto-injected environment, so the caller only needs a key that's
valid enough to reach the function at all, and the anon key is safe even
if this job definition is ever visible to someone.

**Fallback: raw SQL** (`supabase/migrations/0002_schedule_fetch.sql`) does
the same thing by hand if you'd rather not use the dashboard UI - open it,
fill in `YOUR_PROJECT_REF` and your publishable/anon key, and run it in the
SQL Editor. Change `*/10 * * * *` to `0 * * * *` for hourly instead.

Verify: `select * from cron.job;` should list it (`active: true`); after
its first tick, `select * from cron.job_run_details order by start_time
desc limit 5;` should show successful runs. To retarget an existing job's
schedule without recreating it: `select cron.alter_job(job_id := <id>,
schedule := '*/10 * * * *');`.

### 5. Get the frontend's keys
Settings → API. You need two **public-safe** values (not the service_role
one from Step 4):
- **Project URL**
- **anon / public** key

### 6. Point the page at your project
```
copy supabase_config.example.json supabase_config.json
```
Edit `supabase_config.json` with the Project URL and anon key from Step 5,
then:
```
python scripts\build.py
```
Open `index.html` — it should load real data from Supabase. If it shows the
red error screen instead, it's telling you exactly what failed (bad URL/key,
RLS blocking reads, or the table being empty because Step 3's seed step
didn't run).

---

## GitHub + Vercel

1. `git init` (confirm `git --version` works in your terminal first — it
   wasn't on PATH in the tool session that built this).
2. `git add . && git commit -m "Initial commit"`, push to a new GitHub repo.
   `supabase_config.json` stays out of the repo (gitignored) since it's
   environment-specific, even though the anon key itself is safe to expose.
3. Vercel → **Add New Project** → import the repo. Framework preset:
   **Other**. No build command needed — `index.html` at the repo root is
   served as-is. (If you'd rather Vercel bake the config in at deploy time
   instead of committing `supabase_config.json` locally, set
   `SUPABASE_URL`/`SUPABASE_ANON_KEY` as Vercel environment variables and add
   a one-line build command — `python scripts/build.py` — that reads them;
   ask me for this if you want it, it's a small change.)
4. Deploy. Every push to `main` auto-redeploys.

## Local workflow (no Supabase needed, if you just want to edit the page)

Edit `template.html`, then:
```
python scripts\build.py
```
`index.html` is generated — never hand-edit it, changes get overwritten.

To refresh the local reference snapshots in `data/` (not required for the
live page, just useful for testing or reseeding):
```
pip install requests pandas
python scripts\fetch_players.py
python scripts\fetch_fixtures.py
```

## Notes

- `team_logos.json` stays statically embedded — crests essentially never
  change, so there's no reason to burn Supabase reads/storage on them.
- The Artifact version (published at claude.ai) is a separate build: it uses
  Claude's `downloads` capability instead of a plain `Blob` download, and has
  data baked in rather than fetched from Supabase, because neither Supabase
  fetches nor arbitrary downloads are available inside that sandbox.
