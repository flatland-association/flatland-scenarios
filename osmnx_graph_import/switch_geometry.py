"""Switch geometry: which two of a switch's three tracks are its legs (they stay closest together) and which is its
point, and to which side the diverging leg branches off.

All functions take a (multi-)digraph projected to a metric CRS (see `ox.projection.project_graph`), so that lengths
and interpolation are in metres.
"""
import itertools

import networkx as nx
from shapely.geometry import LineString, Point

DISTANCE = 10  # metres along the edge, measured from the switch


def oriented_geometry(graph: nx.MultiDiGraph, u: int, v: int, k: int, start: int) -> LineString:
    """Geometry of edge (u, v, k) as a LineString that starts at node `start`."""
    geom = graph.edges[u, v, k].get("geometry")
    if geom is None:
        # unsimplified graph: the edge is the straight segment between its two nodes
        geom = LineString([(graph.nodes[u]["x"], graph.nodes[u]["y"]),
                           (graph.nodes[v]["x"], graph.nodes[v]["y"])])
    start_point = Point(graph.nodes[start]["x"], graph.nodes[start]["y"])
    if start_point.distance(Point(geom.coords[-1])) < start_point.distance(Point(geom.coords[0])):
        geom = geom.reverse()
    return geom


# If any incident edge is shorter than `distance`, the probing distance is truncated to the shortest incident edge's
# length for ALL of the switch's edges - clipping each edge independently would put a short edge's probe much closer
# to the switch than the others, which could make it look artificially "closest" to every other neighbour.
def switch_probes(graph: nx.MultiDiGraph | nx.DiGraph, switch: int, distance: float = DISTANCE) -> dict[int, Point]:
    """Point on each of `switch`'s incident edges at the (truncated, see note above) probing distance, per neighbour."""
    multi_graph = graph if graph.is_multigraph() else nx.MultiDiGraph(graph)

    incident = ([(switch, v, k, v) for _, v, k in multi_graph.out_edges(switch, keys=True)]
                + [(u, switch, k, u) for u, _, k in multi_graph.in_edges(switch, keys=True)])

    geoms = {neighbour: oriented_geometry(multi_graph, u, v, k, switch) for u, v, k, neighbour in incident}
    probe_distance = min([distance] + [geom.length for geom in geoms.values()])
    return {neighbour: geom.interpolate(probe_distance) for neighbour, geom in geoms.items()}


def legs_from_geometry(graph: nx.MultiDiGraph | nx.DiGraph, switch: int, distance: float = DISTANCE) -> tuple[int, int]:
    """The two neighbours of `switch` whose edges stay closest together, i.e. its legs."""
    probes = switch_probes(graph, switch, distance)
    return min(itertools.combinations(probes, 2), key=lambda pair: probes[pair[0]].distance(probes[pair[1]]))


def _tag_values(graph: nx.MultiDiGraph | nx.DiGraph, switch: int, neighbour: int, tag: str) -> frozenset[str]:
    """Values of OSM tag `tag` of the track between `switch` and `neighbour` (a list where simplification merged OSM
    ways with different values)."""
    data = graph.get_edge_data(switch, neighbour) or graph.get_edge_data(neighbour, switch)
    if graph.is_multigraph():
        data = next(iter(data.values()))
    value = data.get(tag)
    if value is None:
        return frozenset()
    return frozenset(str(v) for v in (value if isinstance(value, list) else [value]))


def through_leg_from_osm_tags(graph: nx.MultiDiGraph | nx.DiGraph, switch: int, point: int, legs: list[int]) -> int | None:
    """The leg the point's track continues into according to OSM: the one continuing the point's OSM way (`osmid`) or,
    else, the only one with the same `service` and `ref` tags (e.g. the main line, not the siding) - None if that
    doesn't decide."""
    point_ways = _tag_values(graph, switch, point, "osmid")
    continuing = [leg for leg in legs if point_ways & _tag_values(graph, switch, leg, "osmid")]
    if len(continuing) == 1:
        return continuing[0]
    same_tags = [leg for leg in legs
                 if all(_tag_values(graph, switch, point, tag) == _tag_values(graph, switch, leg, tag) for tag in ("service", "ref"))]
    if len(same_tags) == 1:
        return same_tags[0]
    return None


# The probes of switch_probes() all lie on a circle around the switch. Coming from the point, going straight through
# the switch leads to the point's probe mirrored through the switch (its antipode on the circle): the straighter leg is
# the one whose probe is closer to it (i.e. the smaller angle).
def through_leg_from_geometry(probes: dict[int, Point], center: Point, point: int, legs: list[int]) -> int:
    """The straighter of `legs` when passing the switch at `center` from `point` (see note above)."""
    straight = Point(2 * center.x - probes[point].x, 2 * center.y - probes[point].y)
    return min(legs, key=lambda leg: probes[leg].distance(straight))


# The forward leg is the through leg: from OSM tags if they tell (see through_leg_from_osm_tags()) - in a curve, it may
# well be the less straight one -, else from geometry (see through_leg_from_geometry()). The diverging leg branches off
# to the right if it lies clockwise of the forward leg (seen from the switch, in the projected CRS with x east and y
# north), i.e. it's a right switch - otherwise to the left.
def switch_legs(graph: nx.MultiDiGraph | nx.DiGraph, switch: int, point: int, distance: float = DISTANCE) -> tuple[int, int, bool]:
    """Return `(forward_leg, diverging_leg, diverges_right)` when passing `switch` from `point` into its legs - the
    through leg from OSM tags, else from geometry (see note above)."""
    probes = switch_probes(graph, switch, distance)
    center = Point(graph.nodes[switch]["x"], graph.nodes[switch]["y"])
    legs = [neighbour for neighbour in probes if neighbour != point]
    assert len(legs) == 2, f"switch {switch} with point {point} has legs {legs}"
    forward = through_leg_from_osm_tags(graph, switch, point, legs)
    if forward is None:
        forward = through_leg_from_geometry(probes, center, point, legs)
    diverging = next(leg for leg in legs if leg != forward)
    f, d = probes[forward], probes[diverging]
    cross = (f.x - center.x) * (d.y - center.y) - (f.y - center.y) * (d.x - center.x)
    return forward, diverging, cross < 0
