from flatland.envs.stations_links import StoppingPoint

from scenario_generator.flatland_integration.flatland_generators import rail_generator_from_grid_map, stations_to_agents_hints, \
    stations_to_stations_links


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


def test_stations_to_stations_links():
    stations = [
        {'id': 2, 'city_position': [5, 2], 'city_orientation': 1, 'station_cells': [[[5, 1], 0], [[5, 2], 1], [[5, 3], 2]]},
        {'id': 1, 'city_position': [2, 3], 'city_orientation': 0, 'station_cells': [[[1, 3], 0], [[2, 3], 1]]},
    ]

    stations_links = stations_to_stations_links(stations)

    # keyed and named by the tool's station id, sorted by id like agents_hints
    assert list(stations_links.stations.keys()) == ['1', '2']
    station = stations_links.stations['1']
    assert station.name == '1'
    assert station.stopping_points == [StoppingPoint(name='1.0', node=(1, 3)), StoppingPoint(name='1.1', node=(2, 3))]
    assert station.edges == [(1, 3), (2, 3)]
    # the tool does not capture station extents yet
    assert station.gates == {}
    assert stations_links.links == []
