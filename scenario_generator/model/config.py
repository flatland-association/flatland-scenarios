"""
Build a single scenario from a Flatland Environment Drawing Tool export and a config.json:

{
  "timetableSpecs": {...},        # optional, same format as in metadata.json; if absent, the tool's timetables are taken unchanged
  "malfunctions": {               # optional, overrides a "malfunctions" section in the tool export key by key
    "breakdown": {"malfunction_interval": 540, "malfunction_duration_min": 20, "malfunction_duration_max": 50},
    "departure": {"malfunction_interval": 5, "malfunction_duration_min": 2, "malfunction_duration_max": 5},
    "scheduled": [{"train": "IC1.0", "step": 42, "duration": 10}, {"handle": 3, "step": 10, "duration": 5}]
  },
  "seed": 42                      # optional
}
"""
import argparse
import json
from pathlib import Path

from flatland.envs.malfunction_generators import MalfunctionParameters
from scenario_generator.model.scenario import Scenario, ScenarioBuilder


def to_malfunction_parameters(specs: dict | None) -> MalfunctionParameters | None:
    if specs is None:
        return None
    return MalfunctionParameters(
        min_duration=specs["malfunction_duration_min"],
        max_duration=specs["malfunction_duration_max"],
        malfunction_rate=1 / specs["malfunction_interval"]
    )


def build_scenario_from_config(initial_scenario: Scenario, config: dict) -> Scenario:
    malfunctions = {**initial_scenario.data.get("malfunctions", {}), **config.get("malfunctions", {})}

    builder = ScenarioBuilder(initial_scenario)
    timetable_specs = config.get("timetableSpecs", None)
    if timetable_specs is None:
        builder.keep_initial_timetables()
    else:
        builder.add_timetables_from_specs(timetable_specs)

    scenario = (
        builder
        .add_malfunction_from_specs(to_malfunction_parameters(malfunctions.get("breakdown", None)))
        .add_departure_malfunction_from_specs(to_malfunction_parameters(malfunctions.get("departure", None)))
        .add_scheduled_malfunctions_from_specs(malfunctions.get("scheduled", None))
        .add_seed_from_specs(config.get("seed", None))
        .build()
    )
    if malfunctions:
        scenario.data["malfunctions"] = malfunctions
    return scenario


def generate_scenario_from_config(initial_scenario_file_name: str, config_file_name: str, name: str, output_folder: Path = None,
                                  create_pkl: bool = True) -> Scenario:
    initial_scenario = Scenario.load(initial_scenario_file_name)
    with open(config_file_name, 'r') as f:
        config = json.load(f)
    scenario = build_scenario_from_config(initial_scenario, config)
    scenario.save(name=name, folder=output_folder, create_pkl=create_pkl)
    return scenario


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Build a scenario (json and pkl) from a drawing tool export and a config.json.")
    parser.add_argument("initial_scenario", help="JSON export of the Flatland Environment Drawing Tool")
    parser.add_argument("config", help="config.json")
    parser.add_argument("name", help="output name (without suffix)")
    parser.add_argument("--output-folder", type=Path, default=Path("."))
    parser.add_argument("--no-pkl", action="store_true")
    args = parser.parse_args()
    generate_scenario_from_config(args.initial_scenario, args.config, args.name, output_folder=args.output_folder, create_pkl=not args.no_pkl)
