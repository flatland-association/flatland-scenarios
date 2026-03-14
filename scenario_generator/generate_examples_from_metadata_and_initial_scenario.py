"""
This file creates the three example scenarios.
"""
from pathlib import Path

from scenario import Scenario, ScenarioBuilder
from utils import load_json


# get initial timetables for the three example scenarios
def get_scene_timetables(scenario: Scenario, scene: str) -> list[dict]:
    if scene == 'all':
        return scenario.timetables
    else:
        raise ValueError(f"unknown scene: {scene}")

def generate_examples_from_metadata_and_initial_scenario(initial_scenario_file_name: str, metadata_file_name: str, levels: list[str] = None, scenarios: list[str] = None,
                                                create_pkl: bool = False, output_folder: Path = None):
    initial_scenario = Scenario.load(initial_scenario_file_name)
    metadata = load_json(metadata_file_name)

    if output_folder is None:
        output_folder = Path(".")

    for level in metadata["levels"]:
        level_name = level["name"]
        if levels is not None and level_name not in levels:
            continue
        for scenario in level["scenarios"]:
            scenario_name_ = scenario["name"]
            if scenarios is not None and scenario_name_ not in scenarios:
                continue

            # merge defaults with scenario-specific specs
            timetable_specs = {**level["defaults"]["timetableSpecs"], **scenario["timetableSpecs"]}
            scenario = ScenarioBuilder(initial_scenario).add_timetables_from_specs(initial_scenario.timetables, timetable_specs).build()
            scenario.save(name=f'{level_name}_{scenario_name_}', folder=output_folder / level_name, create_pkl=create_pkl)


if __name__ == '__main__':
    generate_examples_from_metadata_and_initial_scenario(
        initial_scenario_file_name='examples/example_1/example_1_initial.json',
        metadata_file_name='metadata_example_scenarios.json',
        levels=['example_1'],
        scenarios=['scenario'],
        create_pkl=True,
        output_folder=Path('examples')
    )
    generate_examples_from_metadata_and_initial_scenario(
        initial_scenario_file_name='examples/example_2/example_2_initial.json',
        metadata_file_name='metadata_example_scenarios.json',
        levels=['example_2'],
        scenarios=['scenario'],
        create_pkl=True,
        output_folder=Path('examples')
    )
    generate_examples_from_metadata_and_initial_scenario(
        initial_scenario_file_name='examples/example_3/example_3_initial.json',
        metadata_file_name='metadata_example_scenarios.json',
        levels=['example_3'],
        scenarios=['scenario'],
        create_pkl=True,
        output_folder=Path('examples')
    )
