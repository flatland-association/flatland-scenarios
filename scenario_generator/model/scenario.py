import copy
import json
import math
import uuid
from pathlib import Path
from typing import Tuple, Dict, List, Iterable

import numpy as np

from flatland.core.effects_generator import make_multi_effects_generator
from flatland.envs.grid.rail_env_grid import RailEnvTransitions
from flatland.envs.malfunction_effects_generators import IntermediateStopMalfunctionEffectsGenerator
from flatland.envs.malfunction_generators import MalfunctionParameters, ParamMalfunctionGen
from flatland.envs.persistence import RailEnvPersister
from flatland.envs.rail_env import RailEnv
from flatland.envs.rail_grid_transition_map import RailGridTransitionMap
from flatland.envs.rail_trainrun_data_structures import Waypoint
from flatland.envs.timetable_utils import Line, Timetable
from scenario_generator.flatland_integration.flatland_generators import rail_generator_from_grid_map, line_generator_from_line, \
    timetable_generator_from_timetable
from scenario_generator.flatland_integration.malfunctions import ScheduledMalfunction, ScheduledMalfunctionEffectsGenerator


class Scenario:
    """
    A scenario defines a Flatland env along with some raw information from the Flatland Environment Drawing Tool.
    """

    @property
    def grid(self):
        return self.data['grid']

    @property
    def level_free_crossings(self):
        return self.data['overpasses']

    @property
    def stations(self):
        return self.data['stations']

    @property
    def lines(self):
        return self.data['lines']

    @property
    def timetables(self):
        return self.data['timetables']

    @property
    def train_classes(self):
        return self.data['trainCategories']

    @property
    def flatland_line(self):
        return self.data['flatlandLine']

    @property
    def flatland_timetable(self):
        return self.data['flatlandTimetable']

    def __init__(self, data: dict):
        self.data = copy.deepcopy(data)
        self.malfunction_params: MalfunctionParameters = None
        self.departure_malfunction_params: MalfunctionParameters = None
        self.scheduled_malfunctions: List[ScheduledMalfunction] = []

    @staticmethod
    def load(file_name: str, m=None) -> "Scenario":
        with open(file_name + '.json' if not file_name.endswith(".json") else file_name, 'r') as f:
            data = json.load(f)
            if m is not None:
                data = m(data)
        return Scenario(data)

    def print_lines(self):
        for line in self.lines:
            print(line['name'], line['stationIds'])

    def print_timetables(self):
        for timetable in self.timetables:
            print(timetable['name'])

    def to_rail_generator(self):
        width = self.data['gridDimensions']['cols']
        height = self.data['gridDimensions']['rows']
        grid = RailGridTransitionMap(width=width, height=height, transitions=RailEnvTransitions(), grid=np.array(self.data['grid'], dtype=np.uint16))

        level_free_positions: List[Tuple[int, int]] = [tuple(item) for item in self.data['overpasses']]

        return rail_generator_from_grid_map(grid, level_free_positions, self.stations)

    def to_line_generator(self):
        data = self.data

        agent_positions = [[[tuple(c) for c in coords] for coords in positions] for positions in data['flatlandLine']['agent_positions']]
        agent_directions = data['flatlandLine']['agent_directions']
        agent_targets = [tuple(coords) for coords in data['flatlandLine']['agent_targets']]
        agent_waypoints = {i: [[Waypoint(p, d) for p, d in zip(pa, da)] for pa, da in zip(pas, das)] + [[Waypoint(target, None)]] for i, (pas, das, target)
                           in enumerate(zip(agent_positions, agent_directions, agent_targets))}

        line = Line(
            agent_waypoints=agent_waypoints,
            agent_speeds=data['flatlandLine']['agent_speeds'],
        )
        return line_generator_from_line(line)

    def to_timetable_generator(self, timetable_specs=None):
        scenario = self
        if timetable_specs is not None:
            scenario = ScenarioBuilder(self).add_timetables_from_specs(timetable_specs).build()
        timetable = Timetable(
            earliest_departures=scenario.flatland_timetable['earliest_departures'],
            latest_arrivals=scenario.flatland_timetable['latest_arrivals'],
            max_episode_steps=scenario.flatland_timetable['max_episode_steps']
        )
        return timetable_generator_from_timetable(timetable)

    def to_effects_generator(self):
        effects_generators = []
        if self.departure_malfunction_params is not None:
            effects_generators.append(IntermediateStopMalfunctionEffectsGenerator(**self.departure_malfunction_params._asdict()))
        if self.scheduled_malfunctions:
            effects_generators.append(ScheduledMalfunctionEffectsGenerator(self.scheduled_malfunctions))
        if not effects_generators:
            return None
        if len(effects_generators) == 1:
            return effects_generators[0]
        return make_multi_effects_generator(*effects_generators)

    def to_rail_env(self) -> Tuple[RailEnv, Dict, Dict]:
        data = self.data

        width = data['gridDimensions']['cols']
        height = data['gridDimensions']['rows']

        number_of_agents = len(data['flatlandLine']['agent_positions'])

        env = RailEnv(
            width=width,
            height=height,
            number_of_agents=number_of_agents,
            rail_generator=self.to_rail_generator(),
            line_generator=self.to_line_generator(),
            timetable_generator=self.to_timetable_generator(),
            malfunction_generator=ParamMalfunctionGen(self.malfunction_params) if self.malfunction_params is not None else None,
            effects_generator=self.to_effects_generator(),
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
    """
    The scenario builder takes the JSON output of the Flatland Environment Drawing Tool to create a scenario from the shift and scale parameters.
    """

    def __init__(self, initial_scenario: Scenario):
        self.scenario = Scenario(copy.deepcopy(initial_scenario.data))

        self.scenario_lines = []
        self.scenario_timetables = []
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
        self.malfunction_params: MalfunctionParameters = None
        self.departure_malfunction_params: MalfunctionParameters = None
        self.scheduled_malfunction_specs: List[dict] = []
        self.seed: int = None

    def build(self) -> Scenario:
        self.scenario.data['lines'] = self.scenario_lines
        self.scenario.data['timetables'] = self.scenario_timetables
        self.scenario.data['flatlandLine'] = self.scenario_flatland_line
        self.scenario.data['flatlandTimetable'] = self.scenario_flatland_timetable
        self.scenario.malfunction_params = self.malfunction_params
        self.scenario.departure_malfunction_params = self.departure_malfunction_params
        self.scenario.scheduled_malfunctions = self._resolve_scheduled_malfunctions()
        self.scenario.seed = self.seed
        return self.scenario

    def keep_initial_timetables(self) -> "ScenarioBuilder":
        """
        Take lines and timetables unchanged from the initial scenario (instead of deriving them from timetable specs).
        """
        self.scenario_lines = copy.deepcopy(self.scenario.lines)
        self.scenario_timetables = copy.deepcopy(self.scenario.timetables)
        self.scenario_flatland_line = copy.deepcopy(self.scenario.flatland_line)
        self.scenario_flatland_timetable = copy.deepcopy(self.scenario.flatland_timetable)
        return self

    def add_scheduled_malfunctions_from_specs(self, scheduled_malfunction_specs: List[dict] = None) -> "ScenarioBuilder":
        """
        Each spec is `{"train": <timetable name>, "step": int, "duration": int}` or `{"handle": int, "step": int, "duration": int}`.
        Train names are resolved to agent handles on `build()`, i.e. against the final (derived) timetables.
        """
        self.scheduled_malfunction_specs = list(scheduled_malfunction_specs or [])
        return self

    def _resolve_scheduled_malfunctions(self) -> List[ScheduledMalfunction]:
        if not self.scheduled_malfunction_specs:
            return []
        num_agents = len(self.scenario_flatland_line['agent_positions'])
        # agent handle i is built from timetable i, see add_timetable
        timetable_names = [t['name'] for t in self.scenario_timetables]
        if len(timetable_names) != num_agents:
            raise ValueError(f"Cannot resolve scheduled malfunctions: {len(timetable_names)} timetables but {num_agents} agents in flatlandLine.")

        resolved = []
        for spec in self.scheduled_malfunction_specs:
            if ('train' in spec) == ('handle' in spec):
                raise ValueError(f"Scheduled malfunction {spec} must specify exactly one of 'train' or 'handle'.")
            if 'train' in spec:
                matches = [i for i, name in enumerate(timetable_names) if name == spec['train']]
                if len(matches) != 1:
                    problem = "not found" if not matches else f"ambiguous (handles {matches})"
                    raise ValueError(f"Scheduled malfunction train '{spec['train']}' {problem}. Available trains: {timetable_names}")
                handle = matches[0]
            else:
                handle = spec['handle']
                if not 0 <= handle < num_agents:
                    raise ValueError(f"Scheduled malfunction handle {handle} out of range [0, {num_agents}).")
            step, duration = spec['step'], spec['duration']
            if step < 1 or duration < 1:
                raise ValueError(f"Scheduled malfunction {spec} needs step >= 1 and duration >= 1.")
            resolved.append(ScheduledMalfunction(handle=handle, step=step, duration=duration))
        return resolved

    def rescale_timetable(self, timetable: list[dict], travel_factor: float = 1.0) -> list[dict]:
        stops = timetable['stops']
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
        timetable['stops'] = new_stops
        timetable['travelFactor'] *= travel_factor
        return timetable

    def add_timetable(self, name: str, shift: int, new_name: str, travel_factor: float = None):
        idx, input_timetable = next(((i, s) for i, s in enumerate(self.scenario.timetables) if s['name'] == name), (None, None))
        assert input_timetable is not None, f'timetable {name} not found'

        line = next((l for l in self.scenario.lines if input_timetable['lineId'] == l['id']), None)

        timetable = copy.deepcopy(input_timetable)
        timetable['name'] = new_name
        timetable['id'] = uuid.uuid4().int >> 64

        earliest_departures = []
        latest_arrivals = []

        if travel_factor is not None:
            timetable = self.rescale_timetable(timetable, travel_factor)

        for stop in timetable['stops']:
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

        # append timetable and flatlandTimetable
        self.scenario_timetables.append(timetable)

        self.scenario_flatland_timetable['earliest_departures'].append(earliest_departures)
        self.scenario_flatland_timetable['latest_arrivals'].append(latest_arrivals)
        self.scenario_flatland_timetable['max_episode_steps'] = max(
            self.scenario_flatland_timetable['max_episode_steps'],
            2 * latest_arrivals[-1],
        )

    def sample_timetables(self, num=None):
        if num is None:
            indices = list(range(len(self.scenario.timetables)))
        else:
            indices = np.random.choice(range(len(self.scenario_timetables)), size=num, replace=False)

        self.scenario_timetables = [self.scenario_timetables[i] for i in indices]

        self.scenario_flatland_timetable['earliest_departures'] = [self.scenario_flatland_timetable['earliest_departures'][i] for i in indices]
        self.scenario_flatland_timetable['latest_arrivals'] = [self.scenario_flatland_timetable['latest_arrivals'][i] for i in indices]

        self.scenario_flatland_line['agent_positions'] = [self.scenario_flatland_line['agent_positions'][i] for i in indices]
        self.scenario_flatland_line['agent_directions'] = [self.scenario_flatland_line['agent_directions'][i] for i in indices]
        self.scenario_flatland_line['agent_targets'] = [self.scenario_flatland_line['agent_targets'][i] for i in indices]
        self.scenario_flatland_line['agent_speeds'] = [self.scenario_flatland_line['agent_speeds'][i] for i in indices]

        self.scenario_flatland_timetable['max_episode_steps'] = max(
            [latest_arrivals[-1] for latest_arrivals in self.scenario_flatland_timetable['latest_arrivals']])

    # get consecutive line names by numbering
    @staticmethod
    def _get_new_name(name: str, i: int) -> str:
        if '.' in name:
            prefix, suffix = name.rsplit('.', 1)
        else:
            prefix, suffix = name, '0'
        new_name = f'{prefix}.{int(suffix) + i}'
        return new_name

    @staticmethod
    def _compare(v1, v2):
        if not isinstance(v1, List):
            v1 = [v1]
        if not isinstance(v2, List):
            v2 = [v2]
        return len(set(v1).intersection(set(v2)))

    def add_timetables_from_specs(self, timetable_specs: dict, initial_timetables: list[dict] = None) -> "ScenarioBuilder":
        if initial_timetables is None:
            initial_timetables = self.scenario.timetables
        attribute_filter = timetable_specs.get("attributeFilter", None)
        if attribute_filter is not None:
            key = attribute_filter["key"]
            val = attribute_filter["val"]
            initial_timetables = [s for s in initial_timetables if self._compare(val, s[key])]
        for s in initial_timetables:
            name = s['name']
            train_category_name = s['trainCategory']
            d = timetable_specs["trainCategories"].get(train_category_name, None)
            if d is None:
                continue
            times = d.get('times', 1)
            times = self.sample_from_optional_range(times)
            for i in range(times):
                new_name = self._get_new_name(name, i)
                initial_shift = d.get('initialShift', 0)
                initial_shift = self.sample_from_optional_range(initial_shift)
                periodicty = d.get('periodicity', 0)
                periodicty = self.sample_from_optional_range(periodicty)
                travel_factor = d.get('travelFactor', 1)
                travel_factor = self.sample_from_optional_range(travel_factor)
                self.add_timetable(name, initial_shift + i * periodicty, new_name, travel_factor=travel_factor)
        post_sampler = timetable_specs.get("postSampler", None)
        if post_sampler is not None:
            self.sample_timetables(**post_sampler)
        return self

    @staticmethod
    def sample_from_optional_range(sample_range: int | Iterable[int]) -> int:
        sample = sample_range
        if isinstance(sample_range, Iterable):
            sample = np.random.randint(sample_range[0], sample_range[1])
        return sample

    def add_malfunction_from_specs(self, malfunction_params: MalfunctionParameters = None):
        self.malfunction_params = malfunction_params
        return self

    def add_departure_malfunction_from_specs(self, malfunction_params: MalfunctionParameters = None):
        self.departure_malfunction_params = malfunction_params
        return self

    def add_seed_from_specs(self, seed=None):
        self.seed = seed
        return self
