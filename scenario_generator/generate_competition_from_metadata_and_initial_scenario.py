"""
This file creates all scenes used in the Flatland competition.
There are 5 regions (N,E,S,W,ALL), called 'scenes' (1,2,3,4,5), with W (4) being the combination of N (1) and S (3).
"""
from pathlib import Path

from scenario_generator.scenario import Scenario, ScenarioBuilder
from scenario_generator.utils import load_json


# get initial timetables for one of the 5 scenes / regions
def get_scene_timetables(scenario: Scenario, scene: str) -> list[dict]:
    if scene == 'scene_1':
        return [n for n in scenario.timetables if n['name'].split(' ')[1][0] == '1']
    elif scene == 'scene_2':
        return [n for n in scenario.timetables if n['name'].split(' ')[1][0] == '2']
    elif scene == 'scene_3':
        return [n for n in scenario.timetables if n['name'].split(' ')[1][0] == '3']
    elif scene == 'scene_4':
        return [n for n in scenario.timetables if n['name'].split(' ')[1][0] in ('1', '3', '4')]
    elif scene == 'scene_5':
        return scenario.timetables
    else:
        raise ValueError(f"unknown scene: {scene}")


def display_timetables_for_scene(initial_scenario_file_name: str) -> dict:
    initial_scenario = Scenario.load(initial_scenario_file_name)
    for i in range(1, 6):
        region = f'scene_{i}'
        print(region)
        print([n["name"] for n in get_scene_timetables(initial_scenario, region)])


def generate_competition_from_metadata_and_initial_scenario(initial_scenario_file_name: str, metadata_file_name: str, levels: list[str] = None, scenarios: list[str] = None,
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

            # get initial timetables for scenario
            scene = scenario["scene"]
            timetables_initial_scenario = get_scene_timetables(initial_scenario, scene)
            # merge defaults with scenario-specific specs
            timetable_specs = {**level["defaults"]["timetableSpecs"], **scenario["timetableSpecs"]}
            scenario = ScenarioBuilder(initial_scenario).add_timetables_from_specs(timetables_initial_scenario, timetable_specs).build()
            scenario.save(name=f'{level_name}_{scenario_name_}', folder=output_folder / level_name, create_pkl=create_pkl)


if __name__ == '__main__':
    display_timetables_for_scene('scene_sample_initial.json')
    display_timetables_for_scene('scene_all_initial.json')
    # main(scenario_name='scene_all_initial', config_file='config_template', create_pkl=True)
    generate_competition_from_metadata_and_initial_scenario(
        initial_scenario_file_name='scene_sample_initial.json',
        metadata_file_name='metadata_template.json',
        levels=['level_0'],
        scenarios=['scenario_1'],
        create_pkl=True,
        output_folder=Path('competition')
    )
