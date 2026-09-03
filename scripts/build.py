"""Merge template.html with the team logos + your Supabase config to
produce index.html. Players/fixtures are no longer baked in - the page
fetches those live from Supabase at load time (see README).

Run from anywhere: `python scripts/build.py`
Run this after editing template.html, after re-running fetch_logos.py, or
after changing supabase_config.json.
"""
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
template = (ROOT / "template.html").read_text(encoding="utf-8")

config_path = ROOT / "supabase_config.json"
if not config_path.exists():
    sys.exit(
        "Missing supabase_config.json.\n"
        "Copy supabase_config.example.json to supabase_config.json and fill in\n"
        "your project's URL and anon (public) key - see README Step 6."
    )
config = json.loads(config_path.read_text(encoding="utf-8"))


def safe(text):
    # guard against a stray "</script" inside embedded data breaking the page
    return text.replace("</script", "<\\/script")


logos_json = safe((ROOT / "data" / "team_logos.json").read_text(encoding="utf-8"))
config_json = safe(json.dumps(config))

out = template.replace("__TEAM_LOGOS_JSON__", logos_json)
out = out.replace("__SUPABASE_CONFIG_JSON__", config_json)

out_path = ROOT / "index.html"
out_path.write_text(out, encoding="utf-8")
print(f"wrote {out_path} ({len(out):,} bytes)")
