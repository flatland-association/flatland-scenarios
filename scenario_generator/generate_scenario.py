import json
import copy
import uuid

# scenarios you can choose from
implemented_scenarios = ['scenario_1', 'scenario_2']

# functions
import os
# load JSON
def load_json(name: str) -> dict:
    with open(name + '.json', 'r') as f:
        data = json.load(f)
    return data

# export JSON
def write_json(data: dict, name: str):
    with open(name + '_generated.json', 'w') as f:
        json.dump(data, f, indent=2)
    return
    
# get the name of the new schedule, assuming the format is "{name} {int}.{int}"
def get_new_name(name: str) -> str:
    
    base, number = name.split('.')    
    new_name = base + '.' + str(int(number) + 1)
    
    return new_name

# initialize the flatland line dictionary
def initialize_flatland_line() -> dict:
    flatland_line = {
        'agent_positions': [],
        'agent_directions': [],
        'agent_targets': [],
        'agent_speeds': []
    }
    return flatland_line

# take a schedule, copy and shift it by a given amout
def shift_schedule(schedule: dict, shift: int, initial_shift: bool = False) -> dict:
    
    new_schedule = copy.deepcopy(schedule)
    
    new_schedule['id'] = uuid.uuid4().int >> 64
    if not initial_shift:
        new_schedule['name'] = get_new_name(schedule['name'])
    
    for stop in new_schedule['stops']:
        if stop['earliestDeparture'] is not None: stop['earliestDeparture'] += shift
        if stop['latestArrival'] is not None: stop['latestArrival'] += shift
    
    return new_schedule

# apply a copy and shift multiple times
def multiply_schedule(schedule: dict, shift: int, times: int) -> list:
    
    list_schedules = [schedule]
    
    for _ in range(times - 1): # as the first schedule is given as input
        # duplicate the last entry, except the first time, then take the given input
        schedule_to_duplicate = list_schedules[-1]
        list_schedules.append(shift_schedule(schedule_to_duplicate, shift))
    
    return list_schedules

# get the schedule by name
def get_schedule(data: dict, name: str) -> dict:
    return next((s for s in data['schedules'] if s['name'] == name), None)

# since all schedules start at 0, you can choose the initial "earliest departure"
def create_schedules(data: dict, line: dict, name: str, initial_shift: int, shift: int, times: int) -> list:
    
    schedule = get_schedule(data,name)
    
    initial_schedule = shift_schedule(schedule, initial_shift, initial_shift=True)
    list_schedule = multiply_schedule(initial_schedule, shift, times)
    
    add_flatland_lines(data, line, name, times)
    
    return list_schedule

# add the flatland lines to the dictionary
def add_flatland_lines(data: dict, line: dict, name: str, times: int):
    
    index = next((i for i, s in enumerate(data['schedules']) if s['name'] == name),None)
    
    for _ in range(times):
        line['agent_positions'].append(data['flatland line']['agent_positions'][index])
        line['agent_directions'].append(data['flatland line']['agent_directions'][index])
        line['agent_targets'].append(data['flatland line']['agent_targets'][index])
        line['agent_speeds'].append(data['flatland line']['agent_speeds'][index])
        
    return

# generate the flatland timetables
def generate_flatland_timetables(schedules: list) -> dict:
    
    flatland_timetable = {
        'earliest_departures': [],
        'latest_arrivals': [],
        'max_episode_steps': 0
    }
    
    max_latest_arrival = 0
    
    for schedule in schedules:

        # Timetable data
        earliest_departures = []
        latest_arrivals = []

        for stop in schedule['stops']:
            # The schedule editor disables input for the first arrival and last departure,
            # so their values in the data are null. We just add all of them.
            earliest_departures.append(stop['earliestDeparture'])
            latest_arrivals.append(stop['latestArrival'])

            if stop['latestArrival'] is not None and stop['latestArrival'] > max_latest_arrival:
                max_latest_arrival = stop['latestArrival']

        flatland_timetable['earliest_departures'].append(earliest_departures)
        flatland_timetable['latest_arrivals'].append(latest_arrivals)

    flatland_timetable['max_episode_steps'] = max_latest_arrival * 2
    
    return flatland_timetable

# get coordinates for cells from dict
def get_cell_coordinates(coords: dict) -> str:
    x,y = coords.values()
    return(f'({x},{y})')

# list the schedules
def show_schedules(data: dict):
    for s in data['schedules']:
        name = s['name']
        line_id = s['lineId']

        line = {d['id']: d for d in data['lines']}.get(line_id, {})

        line_name = line.get('name')
        line_stations = line.get('stationIds')
        start_cell = get_cell_coordinates(line.get('startCell'))
        end_cell = get_cell_coordinates(line.get('endCell'))

        #print(name, line_stations, '| start:', start_cell, 'end:', end_cell, '| line: ', line_name)
        print(name, line_stations, '|', start_cell, '-->', end_cell, '| line: ', line_name)
    return



# generate scenarios 
def generate_scenario(scenario_name: str, show_schedule: bool = False):

    assert scenario_name in implemented_scenarios, "Scenario is not implemented. Choose among: " + ", ".join(implemented_scenarios)

    scenario_json = scenario_name + '/' + scenario_name

    # read in the exported file from the drawing tool
    data = load_json(scenario_json)

    # show schedules (to help with the schedule planning)
    if show_schedule:
        show_schedules(data)
    
    # generate the chosen scenario
    if scenario_name == implemented_scenarios[0]: # scenario 1
        data = generate_lines_scenario_1(data)

    # export the modified JSON file
    write_json(data, scenario_json)

    return

# generate scenario_1
def generate_lines_scenario_1(data: dict) -> dict:
    # create the schedules by multiplying each initial schedule
    # initialize flatland line dictionary
    flatland_line = initialize_flatland_line()

    scenario_schedules = []

    for name in ['IC 1.1','IC 2.1','IC 3.1','IC 4.1','IC 5.1','IC 6.1']:
        scenario_schedules += create_schedules(data=data, line=flatland_line, name=name,initial_shift=0,shift=30,times=20)

    for name in ['RE 1.1','RE 2.1','RE 3.1','RE 4.1']:
        scenario_schedules += create_schedules(data=data, line=flatland_line, name=name,initial_shift=0,shift=60,times=10)
        
    for name in ['RE 5.1','RE 6.1','RE 7.1','RE 8.1']:
        scenario_schedules += create_schedules(data=data, line=flatland_line, name=name,initial_shift=10,shift=60,times=10)
        
    for name in ['RE 9.1','RE 10.1','RE 11.1','RE 12.1','RE 13.1','RE 14.1']:
        scenario_schedules += create_schedules(data=data, line=flatland_line, name=name,initial_shift=20,shift=60,times=10)
        
    for name in ['RE 15.1','RE 16.1','RE 17.1','RE 18.1']:
        scenario_schedules += create_schedules(data=data, line=flatland_line, name=name,initial_shift=30,shift=60,times=10)

    for name in ['RE 19.1','RE 20.1','RE 21.1','RE 22.1']:
        scenario_schedules += create_schedules(data=data, line=flatland_line, name=name,initial_shift=10,shift=60,times=10)

    for name in ['RE 23.1','RE 24.1','RE 25.1','RE 26.1']:
        scenario_schedules += create_schedules(data=data, line=flatland_line, name=name,initial_shift=40,shift=60,times=10)
        
    for name in ['RE 50.1','RE 51.1','RE 52.1','RE 53.1']:
        scenario_schedules += create_schedules(data=data, line=flatland_line, name=name,initial_shift=15,shift=60,times=10)
        
    for name in ['RE 54.1','RE 55.1','RE 56.1','RE 57.1']:
        scenario_schedules += create_schedules(data=data, line=flatland_line, name=name,initial_shift=45,shift=60,times=10)

    for name in ['RE 58.1','RE 59.1','RE 60.1','RE 61.1']:
        scenario_schedules += create_schedules(data=data, line=flatland_line, name=name,initial_shift=15,shift=60,times=10)

    for name in ['RE 62.1','RE 63.1','RE 64.1','RE 65.1','RE 66.1','RE 67.1']:
        scenario_schedules += create_schedules(data=data, line=flatland_line, name=name,initial_shift=45,shift=60,times=10)

    for name in ['IR 1.1','IR 2.1','IR 3.1','IR 4.1']:
        scenario_schedules += create_schedules(data=data, line=flatland_line, name=name,initial_shift=0,shift=60,times=10)

    # write the schadules and flatland line into the data dict
    data['schedules'] = scenario_schedules
    data['flatland line'] = flatland_line

    # generate the flatland timetables
    data['flatland timetable'] = generate_flatland_timetables(scenario_schedules)

    return data

# generate scenario_2
def generate_lines_scenario_2(data: dict) -> dict:
    # create the schedules by multiplying each initial schedule
    # initialize flatland line dictionary
    flatland_line = initialize_flatland_line()

    scenario_schedules = []

    for name in ['IC 1.1','IC 2.1','IC 3.1','IC 4.1']:
        scenario_schedules += create_schedules(name=name,initial_shift=0,shift=30,times=20)

    for name in ['RE 1.1','RE 2.1','RE 3.1','RE 4.1','RE 5.1','RE 6.1']:
        scenario_schedules += create_schedules(name=name,initial_shift=0,shift=60,times=10)

    # write the schadules and flatland line into the data dict
    data['schedules'] = scenario_schedules
    data['flatland line'] = flatland_line

    # generate the flatland timetables
    data['flatland timetable'] = generate_flatland_timetables(scenario_schedules)

    return data


if __name__ == '__main__':
    generate_scenario('scenario_2', show_schedule=False)
