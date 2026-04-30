import pickle

from flatland.envs.line_generators import sparse_line_generator
from flatland.envs.rail_env import RailEnv
from flatland.envs.timetable_generators import timetable_generator


def sampling_env_gnerator(env: RailEnv):

    _previous_rail_generator = env.rail_generator

    with open('stations.pkl', 'rb') as f:
        data = pickle.load(f)

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
    env.line_generator = sparse_line_generator()
    env.timetable_generator = timetable_generator

    return env