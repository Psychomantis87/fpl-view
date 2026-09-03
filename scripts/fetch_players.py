"""Pull the FPL bootstrap-static endpoint and write data/players.json.

Run from anywhere: `python scripts/fetch_players.py`
"""
import pathlib
import requests
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "players.json"

data = requests.get("https://fantasy.premierleague.com/api/bootstrap-static/").json()

players = pd.json_normalize(data["elements"])
teams = pd.json_normalize(data["teams"])[["id", "name"]].rename(columns={"id": "team", "name": "team_name"})
positions = pd.json_normalize(data["element_types"])[["id", "singular_name"]].rename(
    columns={"id": "element_type", "singular_name": "player_position"}
)

df = players.merge(teams, on="team", how="left").merge(positions, on="element_type", how="left")
df = df.drop(columns=["price_change_projections", "scout_risks"])  # nested fields, not needed

numeric_string_cols = [
    "form", "ep_next", "ep_this", "points_per_game", "selected_by_percent",
    "value_form", "value_season", "influence", "creativity", "threat", "ict_index",
    "expected_goals", "expected_assists", "expected_goal_involvements",
    "expected_goals_conceded", "price_change_percent",
]
for col in numeric_string_cols:
    df[col] = pd.to_numeric(df[col], errors="coerce")

df["player_name"] = df["first_name"] + " " + df["second_name"]
df["player_price"] = df["now_cost"] / 10  # FPL stores price as tenths (60 = £6.0m)

lead_cols = [
    "id", "player_name", "first_name", "second_name", "web_name",
    "team", "team_name", "element_type", "player_position",
    "now_cost", "player_price",
]
other_cols = [c for c in df.columns if c not in lead_cols]
out = df[lead_cols + other_cols]

OUT.parent.mkdir(parents=True, exist_ok=True)
out.to_json(OUT, orient="records")
print(f"wrote {OUT} ({len(out)} players, {len(out.columns)} columns)")
