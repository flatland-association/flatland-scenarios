import numpy as np

from flatland.core.grid.grid4 import Grid4TransitionsEnum
from flatland.envs.line_generators import sparse_line_generator
from flatland.envs.rail_env import RailEnv
from flatland.envs.timetable_generators import timetable_generator


def sampling_env_gnerator(env: RailEnv):
    height = env.height
    width = env.width

    stations = []
    # 5 in parallel vertically -> E/W
    for r in range(height - 5):
        for c in range(width):
            if np.count_nonzero(env.rail.grid[r:r + 5, c]) == 5:
                stations.append(((r, c), Grid4TransitionsEnum.EAST))
                stations.append(((r, c), Grid4TransitionsEnum.WEST))
    # 5 in parallel horizontally -> N/S
    for r in range(height):
        for c in range(width):
            if np.count_nonzero(env.rail.grid[r, c:c + 5]) == 5:
                stations.append(((r, c), Grid4TransitionsEnum.NORTH))
                stations.append(((r, c), Grid4TransitionsEnum.SOUTH))

    _previous_rail_generator = env.rail_generator

    def rail_generator(*args, **kwargs):
        rail, _ = _previous_rail_generator(*args, **kwargs)
        optionals = {'agents_hints':
            {
                'city_positions': [pos for pos, _ in stations],
                # single-station cities as a workaround
                'train_stations': [[station] for station in stations],
                'city_orientations': [d for _, d in stations],
            },
            'level_free_positions': []
        }
        return rail, optionals

    env.rail_generator = rail_generator
    env.line_generator = sparse_line_generator()
    env.timetable_generator = timetable_generator
    return env
