import pickle

from flatland.envs.line_generators import sparse_line_generator
from flatland.envs.rail_env import RailEnv
from flatland.envs.timetable_generators import timetable_generator


def filter_by_scene(data: dict, scene: str) -> dict:
    scenes = data['scenes_with_station']
    
    filter = [i for i, city_scenes in enumerate(scenes) if scene in city_scenes]
    
    filtered_data = {
        'city_positions': [data['city_positions'][i]    for i in filter],
        'city_orientations': [data['city_orientations'][i] for i in filter],
        'train_stations': [data['train_stations'][i]    for i in filter],
        'scenes_with_station': [data['scenes_with_station'][i] for i in filter],
        'level_free_positions': data['level_free_positions'], 
    }

    return filtered_data

def sampling_env_gnerator(env: RailEnv, line_length: int = 2, scene: str = None) -> RailEnv:

    _previous_rail_generator = env.rail_generator

    with open('stations.pkl', 'rb') as f:
        data = pickle.load(f)

    assert scene is None or scene in {"scene_1", "scene_2", "scene_3", "scene_4", "scene_5"}, "Scene should be 'scene_1', 'scene_2', 'scene_3', 'scene_4', 'scene_5' or None (equivalent to 'scene_5', i.e. all stations)"
    if scene is not None and scene != "scene_5":
        data = filter_by_scene(data, scene)

    city_positions = data["city_positions"]
    city_orientations = data["city_orientations"]
    train_stations = data["train_stations"]
    level_free_positions = data["level_free_positions"]

    def rail_generator(*args, **kwargs):
        rail, _ = _previous_rail_generator(*args, **kwargs)
        optionals = {'agents_hints':
            {
                'city_positions': city_positions,
                'city_orientations': city_orientations,
                'train_stations': train_stations,
            },
            'level_free_positions': level_free_positions
        }
        return rail, optionals

    env.rail_generator = rail_generator
    env.line_generator = sparse_line_generator(line_length=line_length)
    env.timetable_generator = timetable_generator

    return env