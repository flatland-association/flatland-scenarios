import logging

import networkx as nx
import osmnx as ox
import pytest
from shapely.geometry import LineString, Point

import switch_geometry
from switch_geometry import (legs_from_geometry, oriented_geometry, switch_legs, switch_probes, through_leg_from_geometry,
                             through_leg_from_osm_tags)

# Switch 2042222934 of walensee.graphml with its three tracks (u, v, geometry as (lon, lat), OSM tags) - coming from
# its point, switch_legs() classifies it as a right switch. All three tracks are sidings of different OSM ways, so
# OSM doesn't tell which leg the point's track continues into, the geometry decides.
SWITCH = 2042222934
SWITCH_LON_LAT = (9.3441468, 47.0996545)
POINT = 10287687872
FORWARD = 2042222937
DIVERGING = 10287687889
TRACKS = [
    # stored towards the switch, as OSM ways are drawn in any direction
    (POINT, SWITCH, [(9.3444257, 47.0994418), (9.3441468, 47.0996545)], {"osmid": 193705772, "service": "siding"}),
    (SWITCH, FORWARD, [(9.3441468, 47.0996545), (9.3436213, 47.1000539)], {"osmid": 193705776, "service": "siding"}),
    (SWITCH, DIVERGING, [(9.3441468, 47.0996545), (9.3439329, 47.099825), (9.3437387, 47.099998)],
     {"osmid": 193705777, "service": "siding"}),
]


def switch_graph(mirrored: bool, tags: dict[int, dict] | None = None) -> nx.MultiDiGraph:
    """The switch and its three tracks, projected to UTM - `mirrored` (longitude negated) turns right into left.
    `tags` replaces the OSM tags of the track to the given neighbours."""
    sign = -1 if mirrored else 1
    G = nx.MultiDiGraph(crs="epsg:4326")
    lon, lat = SWITCH_LON_LAT
    G.add_node(SWITCH, x=sign * lon, y=lat)
    for u, v, coords, track_tags in TRACKS:
        neighbor = v if u == SWITCH else u
        coords = [(sign * lon, lat) for lon, lat in coords]
        G.add_node(u, x=coords[0][0], y=coords[0][1])
        G.add_node(v, x=coords[-1][0], y=coords[-1][1])
        G.add_edge(u, v, geometry=LineString(coords), **(tags or {}).get(neighbor, track_tags))
    return ox.projection.project_graph(G)


@pytest.mark.parametrize("mirrored", [False, True])
def test_oriented_geometry(mirrored: bool):
    """The switch's three tracks (one stored towards the switch, two away from it), as is and mirrored: each track's
    geometry, oriented from the switch, starts at the switch."""
    G = switch_graph(mirrored)
    switch = Point(G.nodes[SWITCH]["x"], G.nodes[SWITCH]["y"])

    for u, v, k in G.edges(keys=True):
        geom = oriented_geometry(G, u, v, k, SWITCH)

        assert Point(geom.coords[0]).equals_exact(switch, 1e-6)


@pytest.mark.parametrize("mirrored", [False, True])
def test_switch_probes(mirrored: bool):
    """The switch, as is and mirrored, probed at 10 m (shorter than all its tracks): there is one probe per neighbour,
    each 10 m from the switch."""
    G = switch_graph(mirrored)
    switch = Point(G.nodes[SWITCH]["x"], G.nodes[SWITCH]["y"])

    probes = switch_probes(G, SWITCH, distance=10)

    assert set(probes) == {POINT, FORWARD, DIVERGING}
    for probe in probes.values():
        assert probe.distance(switch) == pytest.approx(10, abs=0.01)


def test_switch_probes_truncated_to_shortest_track():
    """The switch probed at 1000 m (longer than all its tracks): every probe lies at the shortest track's length along
    its track - all probes at the same distance, so that the short track's probe doesn't look closest to every other."""
    G = switch_graph(mirrored=False)
    shortest = min(geom.length for _, _, geom in G.edges(data="geometry"))

    probes = switch_probes(G, SWITCH, distance=1000)

    for u, v, k in G.edges(keys=True):
        neighbor = v if u == SWITCH else u
        assert oriented_geometry(G, u, v, k, SWITCH).project(probes[neighbor]) == pytest.approx(shortest)


@pytest.mark.parametrize("mirrored", [False, True])
def test_legs_from_geometry(mirrored: bool):
    """The switch, as is and mirrored: its legs - the two tracks staying closest together - are the forward and the
    diverging one, not the point."""
    assert set(legs_from_geometry(switch_graph(mirrored), SWITCH)) == {FORWARD, DIVERGING}


@pytest.mark.parametrize("mirrored", [False, True])
def test_through_leg_from_geometry(mirrored: bool):
    """The switch, as is and mirrored, passed from its point: the straighter leg is the forward one."""
    G = switch_graph(mirrored)
    center = Point(G.nodes[SWITCH]["x"], G.nodes[SWITCH]["y"])

    assert through_leg_from_geometry(switch_probes(G, SWITCH), center, POINT, [FORWARD, DIVERGING]) == FORWARD
    assert through_leg_from_geometry(switch_probes(G, SWITCH), center, POINT, [DIVERGING, FORWARD]) == FORWARD


@pytest.mark.parametrize("mirrored,diverges_right", [(False, True), (True, False)])
def test_switch_legs(mirrored: bool, diverges_right: bool):
    """The switch with its OSM tags, which don't tell the through leg: the geometry decides, the straighter leg goes
    forward - mirroring keeps which leg goes forward and which diverges, but turns the right switch into a left one."""
    assert switch_legs(switch_graph(mirrored), SWITCH, POINT) == (FORWARD, DIVERGING, diverges_right)


@pytest.mark.parametrize("tags", [
    # the point's OSM way continues into the less straight leg
    {POINT: {"osmid": 1}, FORWARD: {"osmid": 2}, DIVERGING: {"osmid": [3, 1]}},
    # the less straight leg is the only one with the point's tags, the main line, not the siding
    {POINT: {"osmid": 1, "ref": "890"}, FORWARD: {"osmid": 2, "service": "siding"}, DIVERGING: {"osmid": 3, "ref": "890"}},
])
@pytest.mark.parametrize("mirrored,diverges_right", [(False, False), (True, True)])
def test_switch_legs_through_leg_from_osm_tags(tags: dict[int, dict], mirrored: bool, diverges_right: bool):
    """The switch with OSM tags making the less straight leg the through leg (e.g. the main line in a curve): it goes
    forward, and the straighter one diverges - so the right switch becomes a left one, and the mirrored a right one."""
    G = switch_graph(mirrored, tags)

    assert through_leg_from_osm_tags(G, SWITCH, POINT, [FORWARD, DIVERGING]) == DIVERGING
    assert switch_legs(G, SWITCH, POINT) == (DIVERGING, FORWARD, diverges_right)


@pytest.mark.parametrize("clear_angle_difference,warned", [(5, False), (1, True)])
def test_switch_legs_osm_tags_contradict_geometry(clear_angle_difference: float, warned: bool,
                                                  monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture):
    """The switch with OSM tags making the less straight leg the through leg, whose legs deviate from straight by 0.1
    and 1.3 degrees: the tags win either way, but contradicting a clear geometry is warned about - not with the
    default CLEAR_ANGLE_DIFFERENCE (5 degrees), but with 1 degree.

    A real switch warned about with the default (in download_rail_graph("Walenstadt", dist=15000)):
    https://www.openstreetmap.org/node/1338901961 - coming from its point (way
    https://www.openstreetmap.org/way/119090386, service=yard, ref=884), the tags make the leg on way
    https://www.openstreetmap.org/way/119090347 (service=yard, ref=884, 5.9 degrees from straight) the through leg, but
    the leg on way https://www.openstreetmap.org/way/497863617 (service=yard, no ref, 0.8 degrees) is straighter.
    Visually (on the map), the geometry is right: way 497863617 goes straight on, way 119090347 diverges to the left -
    the tags are misleading there (probably a missing ref=884 on way 497863617), see the caveat in switch_legs()."""
    monkeypatch.setattr(switch_geometry, "CLEAR_ANGLE_DIFFERENCE", clear_angle_difference)
    G = switch_graph(False, {POINT: {"osmid": 1}, FORWARD: {"osmid": 2}, DIVERGING: {"osmid": [3, 1]}})

    with caplog.at_level(logging.WARNING, logger="switch_geometry"):
        assert switch_legs(G, SWITCH, POINT)[:2] == (DIVERGING, FORWARD)

    assert (f"switch {SWITCH}: OSM tags make {DIVERGING} the through leg" in caplog.text) == warned


@pytest.mark.parametrize("tags", [
    # the point's OSM way continues into both legs (e.g. a simplified track made of several ways)
    {POINT: {"osmid": [1, 2]}, FORWARD: {"osmid": 1}, DIVERGING: {"osmid": 2}},
    # both legs have the point's tags
    {POINT: {"osmid": 1, "ref": "890"}, FORWARD: {"osmid": 2, "ref": "890"}, DIVERGING: {"osmid": 3, "ref": "890"}},
    # none of the legs has the point's tags
    {POINT: {"osmid": 1, "ref": "890"}, FORWARD: {"osmid": 2, "service": "siding"}, DIVERGING: {"osmid": 3, "service": "crossover"}},
])
def test_switch_legs_osm_tags_undecided(tags: dict[int, dict]):
    """The switch with OSM tags that don't single out one leg: no through leg from OSM, the geometry decides as in
    test_switch_legs()."""
    G = switch_graph(False, tags)

    assert through_leg_from_osm_tags(G, SWITCH, POINT, [FORWARD, DIVERGING]) is None
    assert switch_legs(G, SWITCH, POINT) == (FORWARD, DIVERGING, True)
