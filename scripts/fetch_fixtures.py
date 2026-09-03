"""Pull /api/fixtures/ and write data/team_fixtures.json - the next N
upcoming fixtures per team, with FDR (fixture difficulty rating).

Run from anywhere: `python scripts/fetch_fixtures.py`
"""
import json
import pathlib
import requests

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "team_fixtures.json"
MAX_FIXTURES = 10

bootstrap = requests.get("https://fantasy.premierleague.com/api/bootstrap-static/").json()
fixtures = requests.get("https://fantasy.premierleague.com/api/fixtures/").json()

teams = bootstrap["teams"]
id_to_name = {t["id"]: t["name"] for t in teams}
id_to_short = {t["id"]: t["short_name"] for t in teams}

upcoming = [fx for fx in fixtures if not fx.get("finished") and fx.get("event") is not None]
upcoming.sort(key=lambda fx: (fx["event"], fx.get("kickoff_time") or ""))

team_fixtures = {name: [] for name in id_to_name.values()}
for fx in upcoming:
    h_id, a_id = fx["team_h"], fx["team_a"]
    h_name, a_name = id_to_name.get(h_id), id_to_name.get(a_id)
    h_short, a_short = id_to_short.get(h_id), id_to_short.get(a_id)
    gw = fx["event"]
    if h_name and len(team_fixtures[h_name]) < MAX_FIXTURES:
        team_fixtures[h_name].append({"gw": gw, "opp": a_short, "home": True, "fdr": fx["team_h_difficulty"]})
    if a_name and len(team_fixtures[a_name]) < MAX_FIXTURES:
        team_fixtures[a_name].append({"gw": gw, "opp": h_short, "home": False, "fdr": fx["team_a_difficulty"]})

OUT.parent.mkdir(parents=True, exist_ok=True)
with open(OUT, "w", encoding="utf-8") as f:
    json.dump(team_fixtures, f)
print(f"wrote {OUT} ({len(team_fixtures)} teams, up to {MAX_FIXTURES} fixtures each)")
