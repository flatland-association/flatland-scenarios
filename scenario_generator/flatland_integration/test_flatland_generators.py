import numpy as np
import pytest

from flatland.envs.grid.rail_env_grid import RailEnvTransitions
from flatland.envs.rail_grid_transition_map import RailGridTransitionMap
from flatland.envs.stations_links import Gate, Pin, StoppingPoint

from scenario_generator.flatland_integration.flatland_generators import rail_generator_from_grid_map, stations_to_agents_hints, \
    stations_to_stations_links, group_flat_per_cell_stations

H, V = 1025, 32800  # horizontal and vertical straight


def _grid_map(grid) -> RailGridTransitionMap:
    grid = np.array(grid, dtype=np.uint16)
    return RailGridTransitionMap(width=grid.shape[1], height=grid.shape[0], transitions=RailEnvTransitions(), grid=grid)


def test_stations_to_agents_hints():
    stations = [
        {
            'id': 2,
            'city_position': [5, 4],
            'city_orientation': 1,
            'station_cells': [[[5, 1], 0], [[5, 2], 1], [[5, 3], 2], [[5, 4], 3], [[5, 5], 4], [[5, 6], 5]],
        },
        {
            'id': 1,
            'city_position': [3, 3],
            'city_orientation': 0,
            'station_cells': [[[1, 3], 0], [[2, 3], 1], [[3, 3], 2], [[4, 3], 3], [[5, 3], 4]],
        },
    ]

    hints = stations_to_agents_hints(stations)

    # sorted by station id, not input order
    assert hints['city_positions'] == [(3, 3), (5, 4)]
    assert hints['city_orientations'] == [0, 1]
    assert hints['train_stations'] == [
        [((1, 3), 0), ((2, 3), 1), ((3, 3), 2), ((4, 3), 3), ((5, 3), 4)],
        [((5, 1), 0), ((5, 2), 1), ((5, 3), 2), ((5, 4), 3), ((5, 5), 4), ((5, 6), 5)],
    ]


def test_stations_to_agents_hints_single_cell_station():
    stations = [{'id': 9, 'city_position': [4, 4], 'city_orientation': 1, 'station_cells': [[[4, 4], 0]]}]

    hints = stations_to_agents_hints(stations)

    assert hints['city_positions'] == [(4, 4)]
    assert hints['city_orientations'] == [1]
    assert hints['train_stations'] == [[((4, 4), 0)]]


def test_rail_generator_from_grid_map_without_stations_keeps_legacy_empty_hints():
    # no stations passed -> falls back to the pre-existing placeholder, unchanged behavior
    rail_generator = rail_generator_from_grid_map(grid_map="grid-placeholder", level_free_positions=[(1, 1)], stations=None)
    grid_map, optionals = rail_generator()

    assert grid_map == "grid-placeholder"
    assert optionals == {"agents_hints": {"city_positions": {}}, "level_free_positions": [(1, 1)]}


def test_rail_generator_from_grid_map_with_stations_populates_agents_hints():
    stations = [{'id': 1, 'city_position': [4, 4], 'city_orientation': 1, 'station_cells': [[[4, 4], 0]]}]
    rail_generator = rail_generator_from_grid_map(grid_map="grid-placeholder", level_free_positions=[], stations=stations)
    grid_map, optionals = rail_generator()

    assert optionals['agents_hints'] == stations_to_agents_hints(stations)
    assert optionals['stations_links'] == stations_to_stations_links(stations)


def test_stations_to_stations_links_from_an_older_export():
    # station_cells and no names: named by the tool's station id, sorted by id like agents_hints
    stations = [
        {'id': 2, 'city_position': [5, 2], 'city_orientation': 1, 'station_cells': [[[5, 1], 0], [[5, 2], 1], [[5, 3], 2]]},
        {'id': 1, 'city_position': [2, 3], 'city_orientation': 0, 'station_cells': [[[1, 3], 0], [[2, 3], 1]]},
    ]

    stations_links = stations_to_stations_links(stations)

    assert list(stations_links.stations.keys()) == ['1', '2']
    station = stations_links.stations['1']
    assert station.name == '1'
    assert station.stopping_points == [StoppingPoint(name='1.0', node=(1, 3)), StoppingPoint(name='1.1', node=(2, 3))]
    assert station.edges == [(1, 3), (2, 3)]
    assert station.gates == {}
    assert stations_links.links == []


def test_stations_to_stations_links_keeps_the_name_of_an_older_export():
    # exported with station names but still as station_cells
    stations = [{'id': 3, 'name': 'Ziegelbrücke', 'city_position': [3, 4], 'city_orientation': 1, 'station_cells': [[[2, 4], 0], [[3, 4], 1]]}]

    station = stations_to_stations_links(stations).stations['Ziegelbrücke']

    assert station.stopping_points == [StoppingPoint(name='Ziegelbrücke.0', node=(2, 4)), StoppingPoint(name='Ziegelbrücke.1', node=(3, 4))]


def test_stations_to_stations_links_reads_the_export():
    # as the tool exports a named station with an area: flatland's Station fields with fully qualified names
    stations = [
        {
            'id': 3, 'name': 'Ziegelbrücke', 'city_position': [3, 4], 'city_orientation': 1, 'area': [2, 3, 4, 5],
            'stopping_points': [{'name': 'Ziegelbrücke.0', 'node': [2, 4]}, {'name': 'Ziegelbrücke.1', 'node': [3, 4]}],
            'edges': [[2, 3], [2, 4], [2, 5], [3, 3], [3, 4], [3, 5]],
            'gates': {
                'W': {'name': 'Ziegelbrücke.W', 'pins': {'0': {'name': 'Ziegelbrücke.W.0', 'node': [2, 3]}, '1': {'name': 'Ziegelbrücke.W.1', 'node': [3, 3]}}},
                'E1': {'name': 'Ziegelbrücke.E1', 'pins': {'0': {'name': 'Ziegelbrücke.E1.0', 'node': [2, 5]}}},
            },
        },
        {
            'id': 1, 'name': '1', 'city_position': [3, 56], 'city_orientation': 1,
            'stopping_points': [{'name': '1.0', 'node': [3, 56]}], 'edges': [[3, 56]], 'gates': {},
        },
    ]

    stations_links = stations_to_stations_links(stations)

    assert list(stations_links.stations.keys()) == ['1', 'Ziegelbrücke']
    station = stations_links.stations['Ziegelbrücke']
    assert station.gates == {
        'W': Gate(name='Ziegelbrücke.W', pins={0: Pin(name='Ziegelbrücke.W.0', node=(2, 3)), 1: Pin(name='Ziegelbrücke.W.1', node=(3, 3))}),
        'E1': Gate(name='Ziegelbrücke.E1', pins={0: Pin(name='Ziegelbrücke.E1.0', node=(2, 5))}),
    }
    assert station.stopping_points == [StoppingPoint(name='Ziegelbrücke.0', node=(2, 4)), StoppingPoint(name='Ziegelbrücke.1', node=(3, 4))]
    assert station.edges == [(2, 3), (2, 4), (2, 5), (3, 3), (3, 4), (3, 5)]
    assert stations_links.stations['1'].gates == {}
    assert stations_links.links == []


def test_stations_to_agents_hints_reads_stopping_points():
    stations = [{'id': 1, 'name': 'A', 'city_position': [2, 3], 'city_orientation': 0,
                 'stopping_points': [{'name': 'A.0', 'node': [1, 3]}, {'name': 'A.1', 'node': [2, 3]}], 'edges': [[1, 3], [2, 3]], 'gates': {}}]

    assert stations_to_agents_hints(stations)['train_stations'] == [[((1, 3), 0), ((2, 3), 1)]]


def test_group_flat_per_cell_stations():
    # the flat per-cell format from before this change: one {id, r, c} entry per platform cell, in any order
    grid_map = _grid_map([
        [0, 0, 0, 0],
        [H, H, H, 0],
        [0, 0, 0, V],
        [0, 0, 0, V],
    ])
    stations = [{'id': 2, 'r': 3, 'c': 3}, {'id': 1, 'r': 1, 'c': 2}, {'id': 1, 'r': 1, 'c': 0}, {'id': 2, 'r': 2, 'c': 3}, {'id': 1, 'r': 1, 'c': 1}]

    assert group_flat_per_cell_stations(stations, grid_map) == [
        {'id': 1, 'city_position': [1, 1], 'city_orientation': 1, 'station_cells': [[[1, 0], 0], [[1, 1], 1], [[1, 2], 2]]},
        {'id': 2, 'city_position': [3, 3], 'city_orientation': 0, 'station_cells': [[[2, 3], 0], [[3, 3], 1]]},
    ]


def test_group_flat_per_cell_stations_keeps_other_formats():
    stations = [{'id': 1, 'city_position': [4, 4], 'city_orientation': 1, 'station_cells': [[[4, 4], 0]]}]

    assert group_flat_per_cell_stations(stations, grid_map=None) is stations


def test_rail_generator_from_grid_map_with_flat_per_cell_stations():
    grid_map = _grid_map([[H, H, H]])
    stations = [{'id': 1, 'r': 0, 'c': 0}, {'id': 1, 'r': 0, 'c': 1}, {'id': 1, 'r': 0, 'c': 2}]

    _, optionals = rail_generator_from_grid_map(grid_map, level_free_positions=[], stations=stations)()

    assert optionals['agents_hints'] == {'city_positions': [(0, 1)], 'city_orientations': [1], 'train_stations': [[((0, 0), 0), ((0, 1), 1), ((0, 2), 2)]]}
    assert optionals['stations_links'].stations['1'].stopping_points == [
        StoppingPoint(name='1.0', node=(0, 0)), StoppingPoint(name='1.1', node=(0, 1)), StoppingPoint(name='1.2', node=(0, 2))]


def test_stations_to_stations_links_refuses_duplicate_names():
    stations = [{'id': 1, 'name': 'A', 'city_position': [0, 0], 'city_orientation': 1, 'station_cells': [[[0, 0], 0]]},
                {'id': 2, 'name': 'A', 'city_position': [0, 2], 'city_orientation': 1, 'station_cells': [[[0, 2], 0]]}]

    with pytest.raises(ValueError, match="Two stations are named 'A'"):
        stations_to_stations_links(stations)
