from typing import Dict, List, Tuple

from flatland.envs.rail_grid_transition_map import RailGridTransitionMap
from flatland.envs.stations_links import StationsLinks, Station, StoppingPoint, Gate, Pin
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


def station_name(station: dict) -> str:
    """The station's name from the tool, else its id."""
    return station.get('name') or str(station['id'])


def stations_to_stations_links(stations: List[dict]) -> StationsLinks:
    """
    Convert the Flatland Environment Drawing Tool's grouped station export into
    flatland's stations and links data model
    (https://flatland-association.github.io/flatland-book/environment/environment/stations_links.html).

    Stations are named by the tool's station name, else by its id. Stopping
    points are named <station>.<index> as in sparse_rail_generator, gates
    <station>.<gate> and pins <station>.<gate>.<k>. The tool derives a station's
    tracks (edges), gates and pins from the station area it exports; this only
    names them. Without an area, edges are the station cells. Links are not
    captured yet and stay empty.
    """
    stations_by_id = sorted(stations, key=lambda s: s['id'])
    return StationsLinks(
        stations={
            station_name(s): Station(
                name=station_name(s),
                gates={
                    gate['name']: Gate(
                        name=f"{station_name(s)}.{gate['name']}",
                        pins={k: Pin(name=f"{station_name(s)}.{gate['name']}.{k}", node=tuple(node)) for k, node in enumerate(gate['pins'])},
                    )
                    for gate in s.get('gates', [])
                },
                stopping_points=[StoppingPoint(name=f"{station_name(s)}.{index}", node=tuple(position)) for position, index in s['station_cells']],
                edges=[tuple(cell) for cell in s['edges']] if s.get('edges') else [tuple(position) for position, _ in s['station_cells']],
            )
            for s in stations_by_id
        },
        links=[],
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
