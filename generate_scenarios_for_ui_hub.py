"""
Build several scenarios for the ui-hub import, from drawing-tool exports and configs.

Each scenario folder in the ui-hub gets
- generator.json: the built scenario (scenario generator format),
- scenario.pkl: the RailEnv,
and keeps its hand-written scenario.json (id, title, description) and scenario.png untouched.

Run with the ui-hub backend's Python (it has flatland-rl installed):

    ../flatland-ui-hub/backend/.venv-run/bin/python generate_scenarios_for_ui_hub.py              # all folders
    ../flatland-ui-hub/backend/.venv-run/bin/python generate_scenarios_for_ui_hub.py "2 Türstörung"  # only these
    PYTHONPATH= ../flatland-ui-hub/backend/.venv-run/bin/python generate_scenarios_for_ui_hub.py "2 Türstörung"
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from scenario_generator.model.config import generate_scenario_from_config  # noqa: E402

SCEN = ROOT.parent / "flatland-ui-hub" / "backend" / "app" / "fixtures" / "plan-b"

DRAW = "draw.json"
CONFIG = "config.json"


def main(names: list[str]) -> None:
    """Every scenario folder with a draw.json and a config.json, or only the folders named on the command line."""
    # Like the ui-hub's discovery, folders starting with "_" or "." are left out unless named.
    folders = [SCEN / n for n in names] if names else sorted(
        p for p in SCEN.iterdir() if p.is_dir() and not p.name.startswith(("_", "."))
    )
    for out in folders:
        draw, config = out / DRAW, out / CONFIG
        if not (draw.is_file() and config.is_file()):
            print(f"--- skipped {out.name}: no {DRAW} and {CONFIG}")
            continue
        print(f"==> {out.name}")
        # Saved as generator.json + generator.pkl, then the pkl gets the name the ui-hub expects.
        generate_scenario_from_config(str(draw), str(config), "generator", output_folder=out, create_pkl=True)
        (out / "generator.pkl").replace(out / "scenario.pkl")
        print(f"    {out / 'generator.json'}\n    {out / 'scenario.pkl'}")


if __name__ == "__main__":
    main(sys.argv[1:])
