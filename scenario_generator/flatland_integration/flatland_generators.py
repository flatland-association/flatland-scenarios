from typing import Dict, List, Tuple

from flatland.envs.rail_grid_transition_map import RailGridTransitionMap
from flatland.envs.stations_links import StationsLinks, Station, StoppingPoint, Gate, Pin
from flatland.envs.timetable_utils import Timetable, Line


def stations_to_agents_hints(stations: List[dict]) -> Dict:
    """
    Convert the Flatland Environment Drawing Tool's station export (one entry
    per station: id, city_position, city_orientation, stopping_points) into the
    city_positions/city_orientations/train_stations triple RailEnv's rail
    generators expect under agents_hints.
    """
    stations_by_id = sorted(stations, key=lambda s: s['id'])
    return {
        'city_positions': [tuple(s['city_position']) for s in stations_by_id],
        'city_orientations': [s['city_orientation'] for s in stations_by_id],
        'train_stations': [[(node, index) for index, node in enumerate(_stopping_point_nodes(s))] for s in stations_by_id],
    }


def _stopping_point_nodes(station: dict) -> List[Tuple[int, int]]:
    """The station's stopping point cells in order; older exports list them as station_cells [[r, c], index]."""
    if 'stopping_points' in station:
        return [tuple(sp['node']) for sp in station['stopping_points']]
    return [tuple(position) for position, _ in sorted(station['station_cells'], key=lambda cell: cell[1])]


def stations_to_stations_links(stations: List[dict]) -> StationsLinks:
    """
    Convert the Flatland Environment Drawing Tool's station export into
    flatland's stations and links data model
    (https://flatland-association.github.io/flatland-book/environment/environment/stations_links.html).

    The export uses the model's vocabulary: per station name, stopping_points,
    edges and gates (with pins), named <station>.<index>, <station>.<gate> and
    <station>.<gate>.<k>; the tool derives them from the station area, this
    only reads them. Older exports (station_cells, no names) are named here:
    the station by its id, edges are its stopping points and it has no gates.
    Links are not captured yet and stay empty.
    """
    return StationsLinks(stations={station.name: station for station in (_station(s) for s in sorted(stations, key=lambda s: s['id']))}, links=[])


def _station(s: dict) -> Station:
    if 'stopping_points' not in s:
        name = str(s['id'])
        nodes = _stopping_point_nodes(s)
        return Station(name=name, gates={}, stopping_points=[StoppingPoint(name=f"{name}.{i}", node=node) for i, node in enumerate(nodes)], edges=nodes)
    return Station(
        name=s['name'],
        gates={
            key: Gate(name=gate['name'], pins={int(k): Pin(name=pin['name'], node=tuple(pin['node'])) for k, pin in gate['pins'].items()})
            for key, gate in s.get('gates', {}).items()
        },
        stopping_points=[StoppingPoint(name=sp['name'], node=tuple(sp['node'])) for sp in s['stopping_points']],
        edges=[tuple(cell) for cell in s['edges']],
    )


def rail_generator_from_grid_map(grid_map: RailGridTransitionMap, level_free_positions: List[Tuple[int, int]], stations: List[dict] = None):
    def rail_generator(*args, **kwargs):
        optionals = {
            "agents_hints": stations_to_agents_hints(stations) if stations else {"city_positions": {}},
            "level_free_positions": level_free_positions,
        }
        if stations:
            optionals["stations_links"] = stations_to_stations_links(stations)
        return grid_map, optionals

    return rail_generator


def line_generator_from_line(line: Line):
    def line_generator(*args, **kwargs):
        return line

    return line_generator


def timetable_generator_from_timetable(timetable: Timetable):
    def timetable_generator(*args, **kwargs):
        return timetable

    return timetable_generator
