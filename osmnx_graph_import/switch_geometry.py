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


def closest_neighbors(graph: nx.MultiDiGraph | nx.DiGraph, switch: int, distance: float = DISTANCE) -> tuple[int, int]:
    """The two neighbours of `switch` whose edges stay closest together, i.e. its legs."""
    probes = switch_probes(graph, switch, distance)
    return min(itertools.combinations(probes, 2), key=lambda pair: probes[pair[0]].distance(probes[pair[1]]))


# The probes of switch_probes() all lie on a circle around the switch. Coming from the point, going straight
# through the switch leads to the point's probe mirrored through the switch (its antipode on the circle): the leg
# whose probe is closer to it (i.e. the smaller angle) is the forward leg, the other one diverges. The diverging leg
# branches off to the right if it lies clockwise of the forward leg (seen from the switch, in the projected CRS with
# x east and y north), i.e. it's a right switch - otherwise to the left.
def switch_legs(graph: nx.MultiDiGraph | nx.DiGraph, switch: int, point: int, distance: float = DISTANCE) -> tuple[int, int, bool]:
    """Return `(forward_leg, diverging_leg, diverges_right)` when passing `switch` from `point` into its legs."""
    probes = switch_probes(graph, switch, distance)
    center = Point(graph.nodes[switch]["x"], graph.nodes[switch]["y"])
    straight = Point(2 * center.x - probes[point].x, 2 * center.y - probes[point].y)
    legs = [neighbour for neighbour in probes if neighbour != point]
    assert len(legs) == 2, f"switch {switch} with point {point} has legs {legs}"
    forward, diverging = sorted(legs, key=lambda leg: probes[leg].distance(straight))
    f, d = probes[forward], probes[diverging]
    cross = (f.x - center.x) * (d.y - center.y) - (f.y - center.y) * (d.x - center.x)
    return forward, diverging, cross < 0
