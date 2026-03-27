"""
This file creates all scenes used in the Flatland competition.
There are 5 regions (N,E,S,W,ALL), called 'scenes' (1,2,3,4,5), with W (4) being the combination of N (1) and S (3).
"""
import json
from pathlib import Path
from typing import List

from scenario_generator.examples.generate_examples_from_metadata_and_initial_scenario import derive_scenario_from_initial_scenario_and_metadata
from scenario_generator.model.scenario import Scenario


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


def get_scenes_from_timetable(n) -> List[str]:
    scenes = []
    if n['name'].split(' ')[1][0] == '1':
        scenes.append('scene_1')
    if n['name'].split(' ')[1][0] == '2':
        scenes.append('scene_2')
    if n['name'].split(' ')[1][0] == '3':
        scenes.append('scene_3')
    if n['name'].split(' ')[1][0] in ('1', '3', '4'):
        scenes.append('scene_4')
    scenes.append('scene_5')
    return scenes


def display_timetables_for_scene(initial_scenario_file_name: str) -> dict:
    initial_scenario = Scenario.load(initial_scenario_file_name)
    for i in range(1, 6):
        region = f'scene_{i}'
        print(region)
        print([n["name"] for n in get_scene_timetables(initial_scenario, region)])


def generate_competition_from_metadata_and_initial_scenario(initial_scenario_file_name: str, metadata_file_name: str, levels: list[str] = None,
                                                            scenarios: list[str] = None,
                                                            create_pkl: bool = False, output_folder: Path = None):
    initial_scenario = Scenario.load(initial_scenario_file_name, m=add_scenes_attribute)
    with open(metadata_file_name + '.json' if not metadata_file_name.endswith(".json") else metadata_file_name, 'r') as f:
        metadata = json.load(f)

    if output_folder is None:
        output_folder = Path(".")

    for level_metadata in metadata["levels"]:
        level_name = level_metadata["name"]
        if levels is not None and level_name not in levels:
            continue
        for scenario_metadata in level_metadata["scenarios"]:
            scenario_name_ = scenario_metadata["name"]
            if scenarios is not None and scenario_name_ not in scenarios:
                continue

            # get initial timetables for scenario filtered by scene
            scene = scenario_metadata["scene"]
            scene_timetables = [tt for tt in initial_scenario.timetables if tt["scene"] == scene]

            derived_scenario = derive_scenario_from_initial_scenario_and_metadata(initial_scenario, level_metadata, scenario_metadata,
                                                                                  timetables=scene_timetables)
            derived_scenario.save(name=f'{level_name}_{scenario_name_}', folder=output_folder / level_name, create_pkl=create_pkl)


def add_scenes_attribute(data):
    for timetable in data["timetables"]:
        timetable["scene"] = get_scenes_from_timetable(timetable)


if __name__ == '__main__':
    display_timetables_for_scene('scene_sample_initial.json')
    generate_competition_from_metadata_and_initial_scenario(
        initial_scenario_file_name='scene_sample_initial.json',
        metadata_file_name='metadata_competition_sample.json',
        levels=['level_0'],
        scenarios=['scenario_1'],
        create_pkl=True
    )
