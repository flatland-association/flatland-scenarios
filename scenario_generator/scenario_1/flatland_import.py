import json
import numpy as np

from flatland.envs.grid.rail_env_grid import RailEnvTransitions
from flatland.envs.persistence import RailEnvPersister
from flatland.envs.rail_env import RailEnv
from flatland.envs.rail_grid_transition_map import RailGridTransitionMap
from flatland.envs.rail_trainrun_data_structures import Waypoint
from flatland.envs.timetable_utils import Line, Timetable


def rail_generator_from_grid_map(grid_map, level_free_positions):
    def rail_generator(*args, **kwargs):
        return grid_map, {
            "agents_hints": {"city_positions": {}},
            "level_free_positions": level_free_positions,
        }

    return rail_generator


def line_generator_from_line(line):
    def line_generator(*args, **kwargs):
        return line

    return line_generator


def timetable_generator_from_timetable(timetable):
    def timetable_generator(*args, **kwargs):
        return timetable

    return timetable_generator


def main(generated_json, scenario_pkl):
    with open(generated_json, 'r') as f:
        data = json.load(f)

    width = data['gridDimensions']['cols']
    height = data['gridDimensions']['rows']

    number_of_agents = len(data['flatland line']['agent_positions'])

    agent_positions = [[[tuple(c) for c in coords] for coords in positions] for positions in data['flatland line']['agent_positions']]
    agent_directions = data['flatland line']['agent_directions']
    agent_targets = [tuple(coords[0]) for coords in data['flatland line']['agent_targets']]
    agent_waypoints = {i: [[Waypoint(p, d) for p, d in zip(pa, da)] for pa, da in zip(pas, das)] + [[Waypoint(target, None)]] for i, (pas, das, target)
                       in enumerate(zip(agent_positions, agent_directions, agent_targets))}

    line = Line(
        agent_waypoints=agent_waypoints,
        agent_speeds=data['flatland line']['agent_speeds'],
    )

    timetable = Timetable(
        earliest_departures=data['flatland timetable']['earliest_departures'],
        latest_arrivals=data['flatland timetable']['latest_arrivals'],
        max_episode_steps=data['flatland timetable']['max_episode_steps']
    )

    grid = RailGridTransitionMap(width=width, height=height, transitions=RailEnvTransitions(), grid=np.array(data['grid'], dtype=np.uint16))

    level_free_positions = [tuple(item) for item in data['overpasses']]

    env = RailEnv(
        width=width,
        height=height,
        number_of_agents=number_of_agents,
        rail_generator=rail_generator_from_grid_map(grid, level_free_positions),
        line_generator=line_generator_from_line(line),
        timetable_generator=timetable_generator_from_timetable(timetable),
    )

    env.reset()

    RailEnvPersister.save(env, scenario_pkl)


if __name__ == '__main__':
    main(generated_json='scenario_1_generated.json', scenario_pkl="scenario_1.pkl")
