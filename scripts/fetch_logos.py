"""Pull all 20 club badges from the Premier League's badge CDN and write
data/team_logos.json as {team_name: data-URI}. Club badges rarely change,
so this only needs re-running when the league's team list changes
(promotion/relegation) - not every data refresh.

Run from anywhere: `python scripts/fetch_logos.py`
"""
import base64
import json
import pathlib
import requests

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "team_logos.json"

teams = requests.get("https://fantasy.premierleague.com/api/bootstrap-static/").json()["teams"]

logos = {}
for t in teams:
    url = f"https://resources.premierleague.com/premierleague/badges/50/t{t['code']}.png"
    resp = requests.get(url, timeout=15)
    resp.raise_for_status()
    logos[t["name"]] = "data:image/png;base64," + base64.b64encode(resp.content).decode("ascii")
    print(f"  logo ok: {t['name']} ({len(resp.content)} bytes)")

OUT.parent.mkdir(parents=True, exist_ok=True)
with open(OUT, "w", encoding="utf-8") as f:
    json.dump(logos, f)
print(f"wrote {OUT} ({len(logos)} logos)")
