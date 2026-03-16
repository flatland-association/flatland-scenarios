"""
This file creates the three example scenarios.
"""
import json
from pathlib import Path

from scenario_generator.model.scenario import Scenario, ScenarioBuilder


def generate_examples_from_metadata_and_initial_scenario(initial_scenario_file_name: str, metadata_file_name: str, create_pkl: bool = False, output_folder: Path = None):
    initial_scenario = Scenario.load(initial_scenario_file_name)
    with open(metadata_file_name + '.json' if not metadata_file_name.endswith(".json") else metadata_file_name, 'r') as f:
        metadata = json.load(f)

    if output_folder is None:
        output_folder = Path(".")

    for example in metadata["levels"]:
        example_name = example["name"]

        for scenario in example["scenarios"]:
            scenario_name_ = scenario["name"]

            # merge defaults with scenario-specific specs
            timetable_specs = {**example["defaults"]["timetableSpecs"], **scenario["timetableSpecs"]}
            scenario = ScenarioBuilder(initial_scenario).add_timetables_from_specs(initial_scenario.timetables, timetable_specs).build()
            scenario.save(name=f'{example_name}_{scenario_name_}', folder=output_folder / example_name, create_pkl=create_pkl)


if __name__ == '__main__':
    # generate_examples_from_metadata_and_initial_scenario(
    #     initial_scenario_file_name='example_1/example_1_initial.json',
    #     metadata_file_name='metadata_example_scenarios.json',
    #     create_pkl=True
    # )
    generate_examples_from_metadata_and_initial_scenario(
        initial_scenario_file_name='example_2/example_2_initial.json',
        metadata_file_name='metadata_example_scenarios.json',
        create_pkl=True
    )
    # generate_examples_from_metadata_and_initial_scenario(
    #     initial_scenario_file_name='example_3/example_3_initial.json',
    #     metadata_file_name='metadata_example_scenarios.json',
    #     create_pkl=True,
    # )
