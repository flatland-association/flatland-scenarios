import copy
import json
import math
import uuid
from pathlib import Path
from typing import Tuple, Dict

import numpy as np

from flatland.envs.grid.rail_env_grid import RailEnvTransitions
from flatland.envs.persistence import RailEnvPersister
from flatland.envs.rail_env import RailEnv
from flatland.envs.rail_grid_transition_map import RailGridTransitionMap
from flatland.envs.rail_trainrun_data_structures import Waypoint
from flatland.envs.timetable_utils import Line, Timetable
from scenario_generator.flatland_generators import rail_generator_from_grid_map, line_generator_from_line, timetable_generator_from_timetable
from scenario_generator.utils import load_json


class Scenario:
    """
    The Scenario class takes a dict as input that is the JSON output of the Flatland Environment Drawing Tool
    """

    def __init__(self, data: dict):
        self.data = copy.deepcopy(data)

        self.grid = data['grid']
        self.level_free_crossings = data['overpasses']
        self.stations = data['stations']
        self.lines = data['lines']
        self.schedules = data['schedules']
        self.train_classes = data['trainClasses']
        self.flatland_line = data['flatlandLine']
        self.flatland_timetable = data['flatlandTimetable']

    @staticmethod
    def load(file_name: str) -> "Scenario":
        data = load_json(file_name)
        return Scenario(data)

    def print_lines(self):
        for line in self.lines:
            print(line['name'], line['stationIds'])

    def print_schedules(self):
        for schedule in self.schedules:
            print(schedule['name'])

    def to_rail_env(self) -> Tuple[RailEnv, Dict, Dict]:
        data = self.data

        width = data['gridDimensions']['cols']
        height = data['gridDimensions']['rows']

        number_of_agents = len(data['flatlandLine']['agent_positions'])

        agent_positions = [[[tuple(c) for c in coords] for coords in positions] for positions in data['flatlandLine']['agent_positions']]
        agent_directions = data['flatlandLine']['agent_directions']
        agent_targets = [tuple(coords) for coords in data['flatlandLine']['agent_targets']]
        agent_waypoints = {i: [[Waypoint(p, d) for p, d in zip(pa, da)] for pa, da in zip(pas, das)] + [[Waypoint(target, None)]] for i, (pas, das, target)
                           in enumerate(zip(agent_positions, agent_directions, agent_targets))}

        line = Line(
            agent_waypoints=agent_waypoints,
            agent_speeds=data['flatlandLine']['agent_speeds'],
        )

        timetable = Timetable(
            earliest_departures=data['flatlandTimetable']['earliest_departures'],
            latest_arrivals=data['flatlandTimetable']['latest_arrivals'],
            max_episode_steps=data['flatlandTimetable']['max_episode_steps']
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

        observations, info = env.reset()
        return env, observations, info

    def save(self, name: str, folder: Path = None, create_pkl: bool = False):
        """
        Save in scenario generator format and optionally pkl.
        """
        data = self.data

        if folder is None:
            folder = Path('.')

        file_path = Path(name).with_suffix('.json')
        file_path = folder / file_path
        file_path.parent.mkdir(parents=False, exist_ok=True)

        file_path.write_text(json.dumps(data, indent=2))

        if create_pkl:
            scenario_pkl = f'{name}.pkl'
            env, _, _ = self.to_rail_env()
            RailEnvPersister.save(env, folder / scenario_pkl)


class ScenarioBuilder:
    def __init__(self, initial_scenario: Scenario):
        self.scenario = Scenario(copy.deepcopy(initial_scenario.data))

        self.scenario_lines = []
        self.scenario_schedules = []
        self.scenario_flatland_line = {
            'agent_positions': [],
            'agent_directions': [],
            'agent_targets': [],
            'agent_speeds': []
        }
        self.scenario_flatland_timetable = {
            'earliest_departures': [],
            'latest_arrivals': [],
            'max_episode_steps': 0
        }

    def build(self) -> Scenario:
        self.scenario.data['lines'] = self.scenario_lines
        self.scenario.data['schedules'] = self.scenario_schedules
        self.scenario.data['flatlandLine'] = self.scenario_flatland_line
        self.scenario.data['flatlandTimetable'] = self.scenario_flatland_timetable
        return self.scenario

    def rescale_schedule(self, schedule: list[dict], travel_factor: float = 1.0) -> list[dict]:
        stops = schedule['stops']
        new_stops = copy.deepcopy(stops)  # create new list of adjusted stops
        for i in range(1, len(stops)):
            previous = stops[i - 1]
            current = stops[i]
            new_previous = new_stops[i - 1]
            new_current = new_stops[i]

            original_time = current['latestArrival'] - previous['earliestDeparture']
            dwell_time = current['earliestDeparture'] - current['latestArrival'] if current['earliestDeparture'] is not None else None
            new_current['latestArrival'] = new_previous['earliestDeparture'] + math.ceil(original_time * travel_factor)
            new_current['earliestDeparture'] = new_current['latestArrival'] + dwell_time if i < len(stops) - 1 else None  # no departure from the target
        schedule['stops'] = new_stops
        schedule['travelFactor'] *= travel_factor
        return schedule

    def add_schedule(self, name: str, shift: int, new_name: str, travel_factor: float = None):
        idx, input_schedule = next(((i, s) for i, s in enumerate(self.scenario.schedules) if s['name'] == name), (None, None))
        assert input_schedule is not None, f'schedule {name} not found'

        line = next((l for l in self.scenario.lines if input_schedule['lineId'] == l['id']), None)

        schedule = copy.deepcopy(input_schedule)
        schedule['name'] = new_name
        schedule['id'] = uuid.uuid4().int >> 64

        earliest_departures = []
        latest_arrivals = []

        if travel_factor is not None:
            schedule = self.rescale_schedule(schedule, travel_factor)

        for stop in schedule['stops']:
            if stop['earliestDeparture'] is not None: stop['earliestDeparture'] += shift
            if stop['latestArrival'] is not None: stop['latestArrival'] += shift

            earliest_departures.append(stop['earliestDeparture'])
            latest_arrivals.append(stop['latestArrival'])

        # append line and flatlandLine
        if line not in self.scenario_lines:
            self.scenario_lines.append(line)

        new_flatland_line = self.scenario_flatland_line
        source_line = self.scenario.flatland_line

        new_flatland_line['agent_positions'].append(source_line['agent_positions'][idx])
        new_flatland_line['agent_directions'].append(source_line['agent_directions'][idx])
        new_flatland_line['agent_targets'].append(source_line['agent_targets'][idx])
        new_flatland_line['agent_speeds'].append(source_line['agent_speeds'][idx])

        # append schedule and flatlandTimetable
        self.scenario_schedules.append(schedule)

        self.scenario_flatland_timetable['earliest_departures'].append(earliest_departures)
        self.scenario_flatland_timetable['latest_arrivals'].append(latest_arrivals)
        self.scenario_flatland_timetable['max_episode_steps'] = max(
            self.scenario_flatland_timetable['max_episode_steps'],
            2 * latest_arrivals[-1],
        )

    # get consecutive line names by numbering
    @staticmethod
    def _get_new_name(name: str, i: int) -> str:
        prefix, suffix = name.rsplit('.', 1)
        new_name = f'{prefix}.{int(suffix) + i}'
        return new_name

    def add_schedules_according_to_specs(self, initial_schedule: list[dict], schedule_specs: dict) -> "ScenarioBuilder":
        for s in initial_schedule:
            name = s['name']
            # TODO make not dependent on naming convention
            schedule_spec = name.split(' ')[0]
            d = schedule_specs.get(schedule_spec, None)
            if d is None:
                continue
            for i in range(d.get('times', 1)):
                new_name = self._get_new_name(name, i)
                self.add_schedule(name, d.get('initial shift', 0) + i * d.get('periodicity', 0), new_name, travel_factor=d.get('travel factor', 1))
        return self
