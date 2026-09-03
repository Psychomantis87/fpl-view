// Supabase Edge Function: pulls the FPL API and upserts two rows into
// public.fpl_data ("players", "fixtures"). Triggered on a schedule by the
// pg_cron job set up in Step 4 of the README - not meant to be called by
// the frontend directly (it writes with the service_role key).
import { createClient } from "https://esm.sh/@supabase/supabase-js@2";

const NUMERIC_STRING_COLS = [
  "form", "ep_next", "ep_this", "points_per_game", "selected_by_percent",
  "value_form", "value_season", "influence", "creativity", "threat", "ict_index",
  "expected_goals", "expected_assists", "expected_goal_involvements",
  "expected_goals_conceded", "price_change_percent",
];

function toNumber(v: unknown): number | null {
  if (v === null || v === undefined || v === "") return null;
  const n = Number(v);
  return Number.isNaN(n) ? null : n;
}

async function fetchJson(url: string) {
  const res = await fetch(url);
  if (!res.ok) throw new Error(`${url} -> ${res.status}`);
  return res.json();
}

// Mirrors scripts/fetch_players.py: merge team/position names in, drop the
// two nested fields the page doesn't use, coerce the stringy numeric fields.
async function buildPlayers() {
  const data = await fetchJson("https://fantasy.premierleague.com/api/bootstrap-static/");
  const teamsById = new Map(data.teams.map((t: any) => [t.id, t.name]));
  const posById = new Map(data.element_types.map((p: any) => [p.id, p.singular_name]));

  return data.elements.map((el: any) => {
    const { price_change_projections, scout_risks, ...row } = el;
    for (const col of NUMERIC_STRING_COLS) {
      if (col in row) row[col] = toNumber(row[col]);
    }
    row.team_name = teamsById.get(el.team) ?? null;
    row.player_position = posById.get(el.element_type) ?? null;
    row.player_name = `${el.first_name} ${el.second_name}`;
    row.player_price = el.now_cost / 10;
    return row;
  });
}

// Mirrors scripts/fetch_fixtures.py: next MAX_FIXTURES upcoming fixtures per team.
async function buildFixtures(maxFixtures = 10) {
  const [bootstrap, fixtures] = await Promise.all([
    fetchJson("https://fantasy.premierleague.com/api/bootstrap-static/"),
    fetchJson("https://fantasy.premierleague.com/api/fixtures/"),
  ]);

  const idToName = new Map(bootstrap.teams.map((t: any) => [t.id, t.name]));
  const idToShort = new Map(bootstrap.teams.map((t: any) => [t.id, t.short_name]));

  const upcoming = fixtures
    .filter((fx: any) => !fx.finished && fx.event !== null)
    .sort((a: any, b: any) =>
      a.event - b.event || String(a.kickoff_time).localeCompare(String(b.kickoff_time))
    );

  const teamFixtures: Record<string, any[]> = {};
  for (const name of idToName.values()) teamFixtures[name as string] = [];

  for (const fx of upcoming) {
    const hName = idToName.get(fx.team_h) as string | undefined;
    const aName = idToName.get(fx.team_a) as string | undefined;
    if (hName && teamFixtures[hName].length < maxFixtures) {
      teamFixtures[hName].push({ gw: fx.event, opp: idToShort.get(fx.team_a), home: true, fdr: fx.team_h_difficulty });
    }
    if (aName && teamFixtures[aName].length < maxFixtures) {
      teamFixtures[aName].push({ gw: fx.event, opp: idToShort.get(fx.team_h), home: false, fdr: fx.team_a_difficulty });
    }
  }
  return teamFixtures;
}

const corsHeaders = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type",
};

Deno.serve(async (req) => {
  if (req.method === "OPTIONS") return new Response("ok", { headers: corsHeaders });

  try {
    const supabase = createClient(
      Deno.env.get("SUPABASE_URL")!,
      Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!,
    );

    const [players, fixtures] = await Promise.all([buildPlayers(), buildFixtures()]);
    const now = new Date().toISOString();

    const { error } = await supabase.from("fpl_data").upsert([
      { key: "players", payload: players, updated_at: now },
      { key: "fixtures", payload: fixtures, updated_at: now },
    ]);
    if (error) throw error;

    return new Response(
      JSON.stringify({ ok: true, players: players.length, teams: Object.keys(fixtures).length, at: now }),
      { headers: { ...corsHeaders, "Content-Type": "application/json" } },
    );
  } catch (err) {
    return new Response(JSON.stringify({ ok: false, error: String(err) }), {
      status: 500,
      headers: { ...corsHeaders, "Content-Type": "application/json" },
    });
  }
});
