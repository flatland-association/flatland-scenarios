"""
This file creates the three example scenarios.
"""
import json
from pathlib import Path
from typing import List

from scenario_generator.model.metadata import derive_scenario_from_initial_scenario_and_metadata
from scenario_generator.model.scenario import Scenario


def generate_examples_from_metadata_and_initial_scenario(initial_scenario_file_name: str, metadata_file_name: str, create_pkl: bool = False,
                                                         output_folder: Path = None):
    initial_scenario = Scenario.load(initial_scenario_file_name)
    with open(metadata_file_name + '.json' if not metadata_file_name.endswith(".json") else metadata_file_name, 'r') as f:
        metadata = json.load(f)

    if output_folder is None:
        output_folder = Path(".")

    derive_scenarios_from_initial_scenario_and_metadata(initial_scenario, metadata, output_folder, create_pkl)


def derive_scenarios_from_initial_scenario_and_metadata(initial_scenario: Scenario, metadata, output_folder: Path, create_pkl: bool) -> List[Scenario]:
    scenarios = []
    for level_metadata in metadata["levels"]:
        example_name = level_metadata["name"]

        for scenario_metadata in level_metadata["scenarios"]:
            scenario_name_ = scenario_metadata["name"]

            derived_scenario = derive_scenario_from_initial_scenario_and_metadata(initial_scenario, level_metadata, scenario_metadata)
            derived_scenario.save(name=f'{example_name}_{scenario_name_}', folder=output_folder / example_name, create_pkl=create_pkl)
            scenarios.append(derived_scenario)
    return scenarios


if __name__ == '__main__':
    generate_examples_from_metadata_and_initial_scenario(
        initial_scenario_file_name='example_1/example_1_initial.json',
        metadata_file_name='metadata_example_scenarios.json',
        create_pkl=True
    )
    generate_examples_from_metadata_and_initial_scenario(
        initial_scenario_file_name='example_2/example_2_initial.json',
        metadata_file_name='metadata_example_scenarios.json',
        create_pkl=True
    )
    generate_examples_from_metadata_and_initial_scenario(
        initial_scenario_file_name='example_3/example_3_initial.json',
        metadata_file_name='metadata_example_scenarios.json',
        create_pkl=True,
    )
