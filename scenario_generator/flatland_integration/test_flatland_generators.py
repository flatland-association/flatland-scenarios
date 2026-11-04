from flatland.envs.stations_links import Gate, Pin, StoppingPoint

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
    # without an area there are no gates, and links are not captured yet
    assert station.gates == {}
    assert stations_links.links == []


def test_stations_to_stations_links_uses_the_tool_name():
    stations = [
        {'id': 3, 'name': 'Ziegelbrücke', 'city_position': [2, 4], 'city_orientation': 1, 'station_cells': [[[2, 4], 0], [[3, 4], 1]]},
        {'id': 5, 'city_position': [3, 56], 'city_orientation': 1, 'station_cells': [[[3, 56], 0]]},
    ]

    stations_links = stations_to_stations_links(stations)

    # a named station is keyed by its name, an unnamed one keeps its id
    assert list(stations_links.stations.keys()) == ['Ziegelbrücke', '5']
    assert stations_links.stations['Ziegelbrücke'].stopping_points == [
        StoppingPoint(name='Ziegelbrücke.0', node=(2, 4)), StoppingPoint(name='Ziegelbrücke.1', node=(3, 4)),
    ]


def test_stations_to_stations_links_with_area_and_gates():
    # as the tool exports a station with an area: its tracks as edges, its gates with their pins
    stations = [{
        'id': 1, 'name': 'A', 'city_position': [1, 2], 'city_orientation': 1, 'station_cells': [[[1, 2], 0]],
        'area': [0, 1, 2, 3],
        'edges': [[1, 1], [1, 2], [1, 3], [2, 3]],
        'gates': [{'name': 'W', 'pins': [[1, 1]]}, {'name': 'E1', 'pins': [[1, 3]]}, {'name': 'E2', 'pins': [[2, 3]]}],
    }]

    station = stations_to_stations_links(stations).stations['A']

    assert station.gates == {
        'W': Gate(name='A.W', pins={0: Pin(name='A.W.0', node=(1, 1))}),
        'E1': Gate(name='A.E1', pins={0: Pin(name='A.E1.0', node=(1, 3))}),
        'E2': Gate(name='A.E2', pins={0: Pin(name='A.E2.0', node=(2, 3))}),
    }
    assert station.edges == [(1, 1), (1, 2), (1, 3), (2, 3)]
    assert station.stopping_points == [StoppingPoint(name='A.0', node=(1, 2))]
