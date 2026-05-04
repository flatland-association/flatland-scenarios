import pickle
import numpy as np
from typing import List
from numpy.random.mtrand import RandomState
from importlib.resources import files

from flatland.envs.line_generators import sparse_line_generator
from flatland.envs.rail_env import RailEnv
from flatland.core.grid.grid4 import Grid4TransitionsEnum
from flatland.envs.agent_utils import EnvAgent
from flatland.envs.grid.distance_map import DistanceMap
from flatland.envs.timetable_utils import Timetable
from flatland.envs.timetable_generators import len_handle_none


# adaptaion of timetable generator for lines with length > 2
def timetable_generator(agents: List[EnvAgent], distance_map: DistanceMap,
                        agents_hints: dict, np_random: RandomState = None) -> Timetable:
    """
    Calculates earliest departure and latest arrival times for the agents
    This is the new addition in Flatland 3
    Also calculates the max episodes steps based on the density of the timetable

    inputs:
        agents - List of all the agents rail_env.agents
        distance_map - Distance map of positions to targets of each agent in each direction
        agent_hints - Uses the number of cities
        np_random - RNG state for seeding
    returns:
        Timetable with the latest_arrivals, earliest_departures and max_episdode_steps
    """
    # max_episode_steps calculation
    if agents_hints:
        city_positions = agents_hints['city_positions']
        num_cities = len(city_positions)
    else:
        num_cities = 2

    timedelay_factor = 4
    alpha = 2
    num_agents = len(agents)
    max_episode_steps = int(timedelay_factor * alpha * \
                            (distance_map.rail.width + distance_map.rail.height + (num_agents / num_cities)))

    # Multipliers
    old_max_episode_steps_multiplier = 3.0
    new_max_episode_steps_multiplier = 1.5
    travel_buffer_multiplier = 1.3  # must be strictly lesser than new_max_episode_steps_multiplier
    assert new_max_episode_steps_multiplier > travel_buffer_multiplier
    end_buffer_multiplier = 0.05
    mean_shortest_path_multiplier = 0.2

    if len(agents[0].waypoints) > 1:
        # distance for intermediates parts and sum up
        max_line_length = max(len(a.waypoints) - 1 for a in agents)
        fake_agents = []
        fake_agent_tracker = {}
        for i in range(max_line_length):
            for a in agents:
                waypoints = a.waypoints
                if i >= len(waypoints) - 1:
                    continue
                fake_handle = len(fake_agents)  
                fake_agent_tracker[fake_handle] = a.handle 

                fake_agents.append(EnvAgent(
                    handle=fake_handle,
                    initial_configuration=(waypoints[i][0].position, waypoints[i][0].direction),
                    # N.B. routing flexibility is ignored by this timetable generator
                    current_configuration=(waypoints[i][0].position, waypoints[i][0].direction),
                    old_configuration=(None, None),
                    targets={(waypoints[i + 1][0].position, d) for d in Grid4TransitionsEnum},
                ))
        distance_map_with_intermediates = DistanceMap(fake_agents, distance_map.env_height, distance_map.env_width)
        distance_map_with_intermediates.reset(fake_agents, distance_map.rail)

        shortest_paths = distance_map_with_intermediates.get_shortest_paths()
        shortest_path_segment_lengths = [[] for _ in range(num_agents)]
        for k, v in shortest_paths.items():
            shortest_path_segment_lengths[fake_agent_tracker[k]].append(len_handle_none(v))
        shortest_paths_lengths = [sum(l) for l in shortest_path_segment_lengths]
    else:
        shortest_paths = distance_map.get_shortest_paths()
        shortest_paths_lengths = [len_handle_none(v) for k, v in shortest_paths.items()]
        shortest_path_segment_lengths = [[l] for l in shortest_paths_lengths]

    # Find mean_shortest_path_time
    agent_speeds = [agent.speed_counter.speed for agent in agents]
    agent_shortest_path_times = np.array(shortest_paths_lengths) / np.array(agent_speeds)
    mean_shortest_path_time = np.mean(agent_shortest_path_times)

    # Deciding on a suitable max_episode_steps
    longest_speed_normalized_time = np.max(agent_shortest_path_times)
    mean_path_delay = mean_shortest_path_time * mean_shortest_path_multiplier
    max_episode_steps_new = int(np.ceil(longest_speed_normalized_time * new_max_episode_steps_multiplier) + mean_path_delay)

    max_episode_steps_old = int(max_episode_steps * old_max_episode_steps_multiplier)

    max_episode_steps = min(max_episode_steps_new, max_episode_steps_old)

    end_buffer = int(max_episode_steps * end_buffer_multiplier)
    latest_arrival_max = max_episode_steps - end_buffer

    earliest_departures = []
    latest_arrivals = []

    for agent in agents:
        agent_shortest_path_time = agent_shortest_path_times[agent.handle]
        agent_travel_time_max = int(np.ceil((agent_shortest_path_time * travel_buffer_multiplier) + mean_path_delay))

        departure_window_max = max(latest_arrival_max - agent_travel_time_max, 1)

        earliest_departure = np_random.randint(0, departure_window_max)
        latest_arrival = earliest_departure + agent_travel_time_max

        agent.earliest_departure = earliest_departure
        agent.latest_arrival = latest_arrival
        ed = earliest_departure
        eds = [earliest_departure]
        for l in shortest_path_segment_lengths[agent.handle]:
            ed += l
            eds.append(ed)
        la = latest_arrival
        las = [latest_arrival]
        for l in reversed(shortest_path_segment_lengths[agent.handle]):
            la -= l
            las.insert(0, la)
        eds[-1] = None
        las[0] = None
        earliest_departures.append(eds)
        latest_arrivals.append(las)

    return Timetable(earliest_departures=earliest_departures, latest_arrivals=latest_arrivals,
                     max_episode_steps=max_episode_steps)


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


def sampling_env_generator(env: RailEnv, line_length: int = 2, scene: str = None) -> RailEnv:

    _previous_rail_generator = env.rail_generator
 
    with files('competitions.competition_2026').joinpath('stations.pkl').open('rb') as f:
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