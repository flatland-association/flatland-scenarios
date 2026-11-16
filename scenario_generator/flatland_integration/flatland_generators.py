from typing import Dict, List, Optional, Tuple

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
    only reads them. Older exports (station_cells) are named here: the station
    by its name if it has one, else by its id; edges are its stopping points
    and it has no gates.
    Links are not captured yet and stay empty.
    Two stations with the same name are refused, as one would replace the other.
    """
    by_name: Dict[str, Station] = {}
    for s in sorted(stations, key=lambda s: s['id']):
        station = _station(s)
        if station.name in by_name:
            raise ValueError(f"Two stations are named '{station.name}'; station names must be unique.")
        by_name[station.name] = station
    return StationsLinks(stations=by_name, links=[])


def _station(s: dict) -> Station:
    if 'stopping_points' not in s:
        # Exported before the stations_links vocabulary: named if the tool had a name for it.
        name = s.get('name') or str(s['id'])
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


def group_flat_per_cell_stations(stations: List[dict], grid_map: RailGridTransitionMap) -> List[dict]:
    """
    Group a station export in the flat per-cell format (one {id, r, c} entry per
    platform cell, as the drawing tool wrote before this change) into the
    station_cells format: one entry per station with id, city_position,
    city_orientation and station_cells, as the tool does on export: cells in
    row-major order, city_position the middle cell, city_orientation 1 if
    that cell is a horizontal straight, else 0.
    Exports in the station_cells or stations_links format are returned unchanged.
    """
    if not any('r' in s for s in stations):
        return stations
    cells_by_id: Dict[int, List[Tuple[int, int]]] = {}
    for s in stations:
        cells_by_id.setdefault(s['id'], []).append((s['r'], s['c']))
    grouped = []
    for station_id, cells in sorted(cells_by_id.items()):
        cells.sort()
        r, c = cells[len(cells) // 2]
        # stations sit on straights: a horizontal straight lets a train facing east (1) continue east
        is_horizontal = bool(grid_map.transitions.get_transition(int(grid_map.grid[r, c]), 1, 1))
        grouped.append({
            'id': station_id,
            'city_position': [r, c],
            'city_orientation': 1 if is_horizontal else 0,
            'station_cells': [[[cell_r, cell_c], index] for index, (cell_r, cell_c) in enumerate(cells)],
        })
    return grouped


def rail_generator_from_grid_map(grid_map: RailGridTransitionMap, level_free_positions: List[Tuple[int, int]], stations: Optional[List[dict]] = None):
    if stations:
        stations = group_flat_per_cell_stations(stations, grid_map)

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
