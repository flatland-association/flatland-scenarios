import json
import copy
import math
import uuid
from pathlib import Path


# load JSON from Flatland Drawing Tool
def load_json(name: str) -> dict:
    with open(name + '.json', 'r') as f:
        data = json.load(f)
    return data

# get consecutive line names by numbering     
def get_new_name(name: str, i: int) -> str:
    prefix, suffix = name.rsplit('.', 1)
    new_name = f'{prefix}.{int(suffix) + i}'
    return new_name

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
        self.flatland_line = data['flatland line']
        self.flatland_timetable = data['flatland timetable']
        
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

    def print_lines(self):
        for line in self.lines:
            print(line['name'], line['stationIds'])

    def print_schedules(self):
        for schedule in self.schedules:
            print(schedule['name'])

    def rescale_schedule(self, schedule: list[dict], travel_factor: float = 1.0) -> list[dict]:
        stops = schedule['stops']
        new_stops = copy.deepcopy(stops) # create new list of adjusted stops
        for i in range(1, len(stops)):
            previous = stops[i-1]
            current = stops[i]
            new_previous = new_stops[i-1]
            new_current = new_stops[i]

            original_time = current['latestArrival'] - previous['earliestDeparture']
            dwell_time = current['earliestDeparture'] - current['latestArrival'] if current['earliestDeparture'] is not None else None
            new_current['latestArrival'] = new_previous['earliestDeparture'] + math.ceil(original_time * travel_factor)
            new_current['earliestDeparture'] = new_current['latestArrival'] + dwell_time if i < len(stops) - 1 else None # no departure from the target
        schedule['stops']= new_stops
        schedule['travelFactor'] *= travel_factor
        return schedule
    
    def add_schedule(self, name: str, shift: int, new_name: str, travel_factor: float = None):
        idx, input_schedule = next(((i,s) for i,s in enumerate(self.schedules) if s['name'] == name), (None, None))
        assert input_schedule is not None, f'schedule {name} not found'

        line = next((l for l in self.lines if input_schedule['lineId'] == l['id']), None)
        
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
        
        # append line and flatland line
        if line not in self.scenario_lines:
            self.scenario_lines.append(line)
        
        new_flatland_line = self.scenario_flatland_line
        source_line = self.flatland_line

        new_flatland_line['agent_positions'].append(source_line['agent_positions'][idx])
        new_flatland_line['agent_directions'].append(source_line['agent_directions'][idx])
        new_flatland_line['agent_targets'].append(source_line['agent_targets'][idx])
        new_flatland_line['agent_speeds'].append(source_line['agent_speeds'][idx])
        
        # append schedule and flatland timetable
        self.scenario_schedules.append(schedule)
        
        self.scenario_flatland_timetable['earliest_departures'].append(earliest_departures)
        self.scenario_flatland_timetable['latest_arrivals'].append(latest_arrivals)
        self.scenario_flatland_timetable['max_episode_steps'] = max(
            self.scenario_flatland_timetable['max_episode_steps'],
            2 * latest_arrivals[-1],
        )

    def add_schedules_from_dict(self, initial_schedule: list[dict], schedule_dict: dict):
        for s in initial_schedule:
            name = s['name']
            key = name.split(' ')[0]
            d = schedule_dict.get(key, None)
            if d is None:
                continue
            for i in range(d.get('times',1)):
                new_name = get_new_name(name, i)
                self.add_schedule(name, d.get('initial shift',0) + i*d.get('periodicity',0), new_name, travel_factor=d.get('travel factor',1))

    def save(self, name: str, folder: str = None, create_pkl: bool = False):
        data = copy.deepcopy(self.data)
        data['lines'] = self.scenario_lines
        data['schedules'] = self.scenario_schedules
        data['flatland line'] = self.scenario_flatland_line
        data['flatland timetable'] = self.scenario_flatland_timetable

        file_path = Path(name).with_suffix('.json')

        if folder:
            file_path = Path(folder) / file_path
            file_path.parent.mkdir(parents=False, exist_ok=True)

        file_path.write_text(json.dumps(data, indent=2))

        if create_pkl:
            import flatland_import as fi
            fi.main(scenario_json=f'{name}.json', scenario_pkl=f'{name}.pkl', folder=folder)

