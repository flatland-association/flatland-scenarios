import networkx as nx
import osmnx as ox
import pytest
from shapely.geometry import LineString, Point

from switch_geometry import closest_neighbors, oriented_geometry, switch_legs, switch_probes

# Switch 2042222934 of walensee.graphml with its three tracks (u, v, geometry as (lon, lat)) - coming from its point,
# switch_legs() classifies it as a right switch.
SWITCH = 2042222934
SWITCH_LON_LAT = (9.3441468, 47.0996545)
POINT = 10287687872
FORWARD = 2042222937
DIVERGING = 10287687889
TRACKS = [
    # stored towards the switch, as OSM ways are drawn in any direction
    (POINT, SWITCH, [(9.3444257, 47.0994418), (9.3441468, 47.0996545)]),
    (SWITCH, FORWARD, [(9.3441468, 47.0996545), (9.3436213, 47.1000539)]),
    (SWITCH, DIVERGING, [(9.3441468, 47.0996545), (9.3439329, 47.099825), (9.3437387, 47.099998)]),
]


def switch_graph(mirrored: bool) -> nx.MultiDiGraph:
    """The switch and its three tracks, projected to UTM - `mirrored` (longitude negated) turns right into left."""
    sign = -1 if mirrored else 1
    G = nx.MultiDiGraph(crs="epsg:4326")
    lon, lat = SWITCH_LON_LAT
    G.add_node(SWITCH, x=sign * lon, y=lat)
    for u, v, coords in TRACKS:
        coords = [(sign * lon, lat) for lon, lat in coords]
        G.add_node(u, x=coords[0][0], y=coords[0][1])
        G.add_node(v, x=coords[-1][0], y=coords[-1][1])
        G.add_edge(u, v, geometry=LineString(coords))
    return ox.projection.project_graph(G)


@pytest.mark.parametrize("mirrored", [False, True])
def test_oriented_geometry(mirrored: bool):
    G = switch_graph(mirrored)
    switch = Point(G.nodes[SWITCH]["x"], G.nodes[SWITCH]["y"])

    for u, v, k in G.edges(keys=True):
        geom = oriented_geometry(G, u, v, k, SWITCH)

        assert Point(geom.coords[0]).equals_exact(switch, 1e-6)


@pytest.mark.parametrize("mirrored", [False, True])
def test_switch_probes(mirrored: bool):
    G = switch_graph(mirrored)
    switch = Point(G.nodes[SWITCH]["x"], G.nodes[SWITCH]["y"])

    probes = switch_probes(G, SWITCH, distance=10)

    assert set(probes) == {POINT, FORWARD, DIVERGING}
    for probe in probes.values():
        assert probe.distance(switch) == pytest.approx(10, abs=0.01)


def test_switch_probes_truncated_to_shortest_track():
    G = switch_graph(mirrored=False)
    shortest = min(geom.length for _, _, geom in G.edges(data="geometry"))

    probes = switch_probes(G, SWITCH, distance=1000)

    # all probes at the same distance, so that the short track's probe doesn't look closest to every other
    for u, v, k in G.edges(keys=True):
        neighbor = v if u == SWITCH else u
        assert oriented_geometry(G, u, v, k, SWITCH).project(probes[neighbor]) == pytest.approx(shortest)


@pytest.mark.parametrize("mirrored", [False, True])
def test_closest_neighbors(mirrored: bool):
    assert set(closest_neighbors(switch_graph(mirrored), SWITCH)) == {FORWARD, DIVERGING}


@pytest.mark.parametrize("mirrored,diverges_right", [(False, True), (True, False)])
def test_switch_legs(mirrored: bool, diverges_right: bool):
    # mirroring keeps which leg goes straight on and which diverges, but turns the right switch into a left one
    assert switch_legs(switch_graph(mirrored), SWITCH, POINT) == (FORWARD, DIVERGING, diverges_right)
