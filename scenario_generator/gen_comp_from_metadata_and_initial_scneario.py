"""
This file creates all scenes used in the Flatland competition.
There are 5 regions (N,E,S,W,ALL), called 'scenes' (1,2,3,4,5), with W (4) being the combination of N (1) and S (3).
"""
from scenario_generator.scenario import Scenario, ScenarioBuilder
from scenario_generator.utils import load_json


# get initial schedules for one of the 5 scenes / regions
def get_scene_schedules(scenario: Scenario, scene: str) -> list[dict]:
    if scene == 'scene_1':
        return [n for n in scenario.schedules if n['name'].split(' ')[1][0] == '1']
    elif scene == 'scene_2':
        return [n for n in scenario.schedules if n['name'].split(' ')[1][0] == '2']
    elif scene == 'scene_3':
        return [n for n in scenario.schedules if n['name'].split(' ')[1][0] == '3']
    elif scene == 'scene_4':
        return [n for n in scenario.schedules if n['name'].split(' ')[1][0] in ('1', '3', '4')]
    elif scene == 'scene_5':
        return scenario.schedules
    else:
        raise ValueError(f"unknown scene: {scene}")


# use level defaults unless overridden by scene
def get_scenario_schedule_dict(config: dict, level: str, scene: str) -> dict:
    assert level in config.keys(), f"no level: '{level}' in config file"
    assert scene in config[level].keys(), f"no scene: '{scene}' in level: '{level}' in config file"

    default_dict = config[level]['defaults']['schedules']
    scene_dict = config[level][scene]['schedules']
    dict_scenario_schedule = {
        key: default_dict.get(key, {}) | scene_dict.get(key, {})
        for key in (default_dict.keys() | scene_dict.keys())
    }
    return dict_scenario_schedule


def main(initial_scenario_file_name: str, metadata_file_name: str, levels: list[str] = None, scenes: list[str] = None, create_pkl: bool = False):
    initial_scenario = Scenario.load(initial_scenario_file_name)
    metadata = load_json(metadata_file_name)

    if levels is None:
        levels = list(metadata.keys())

    for level in levels:
        if scenes is None:
            scenes = list(metadata[level].keys())
            scenes.remove('defaults')

        # nomenclature: scene = region
        for scene in scenes:
            schedule_initial_scenario = get_scene_schedules(initial_scenario, scene)
            stretch_and_fold_config_from_metadata = get_scenario_schedule_dict(metadata, level, scene)
            scenario = ScenarioBuilder(initial_scenario).add_schedules_from_dict(schedule_initial_scenario, stretch_and_fold_config_from_metadata).build()
            scenario.save(name=f'{level}_{scene}', folder=f'{level}', create_pkl=create_pkl)


if __name__ == '__main__':
    # main(scenario_name='scene_all_initial', config_file='config_template', create_pkl=True)
    main(
        initial_scenario_file_name='scene_all_initial.json',
        metadata_file_name='metadata_template.json',
        levels=['level_0'],
        scenes=['scene_1'],
        create_pkl=True
    )
