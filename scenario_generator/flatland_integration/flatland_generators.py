from typing import Dict, List, Tuple

from flatland.envs.rail_grid_transition_map import RailGridTransitionMap
from flatland.envs.timetable_utils import Timetable, Line


def stations_to_agents_hints(stations: List[dict]) -> Dict:
    """
    Convert the Flatland Environment Drawing Tool's grouped station export
    (one entry per station: id, city_position, city_orientation, station_cells)
    into the city_positions/city_orientations/train_stations triple RailEnv's
    rail generators expect under agents_hints.
    """
    stations_by_id = sorted(stations, key=lambda s: s['id'])
    return {
        'city_positions': [tuple(s['city_position']) for s in stations_by_id],
        'city_orientations': [s['city_orientation'] for s in stations_by_id],
        'train_stations': [[(tuple(position), index) for position, index in s['station_cells']] for s in stations_by_id],
    }


def rail_generator_from_grid_map(grid_map: RailGridTransitionMap, level_free_positions: List[Tuple[int, int]], stations: List[dict] = None):
    def rail_generator(*args, **kwargs):
        return grid_map, {
            "agents_hints": stations_to_agents_hints(stations) if stations else {"city_positions": {}},
            "level_free_positions": level_free_positions,
        }

    return rail_generator


def line_generator_from_line(line: Line):
    def line_generator(*args, **kwargs):
        return line

    return line_generator


def timetable_generator_from_timetable(timetable: Timetable):
    def timetable_generator(*args, **kwargs):
        return timetable

    return timetable_generator
