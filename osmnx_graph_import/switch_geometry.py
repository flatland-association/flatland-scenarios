"""Switch geometry: which two of a switch's three tracks are its legs (they stay closest together) and which is its
point, and to which side the diverging leg branches off.

All functions take a (multi-)digraph projected to a metric CRS (see `ox.projection.project_graph`), so that lengths
and interpolation are in metres.
"""
import itertools
import logging
import math

import networkx as nx
from shapely.geometry import LineString, Point

logger = logging.getLogger(__name__)

DISTANCE = 10  # metres along the edge, measured from the switch
# degrees by which one leg must be straighter than the other for the geometry to clearly tell the through leg - in
# walensee.graphml and sargans_reversing_loop.graphml, the legs differ by 0.1-3.8 degrees, in curved switches by 2-4
CLEAR_ANGLE_DIFFERENCE = 5


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
# the one deviating less from it.
def deviation_from_straight(probes: dict[int, Point], center: Point, point: int, leg: int) -> float:
    """Degrees by which `leg` deviates from going straight through the switch at `center` from `point`."""
    sx, sy = center.x - probes[point].x, center.y - probes[point].y
    lx, ly = probes[leg].x - center.x, probes[leg].y - center.y
    return abs(math.degrees(math.atan2(sx * ly - sy * lx, sx * lx + sy * ly)))


def through_leg_from_geometry(probes: dict[int, Point], center: Point, point: int, legs: list[int]) -> int:
    """The straighter of `legs` when passing the switch at `center` from `point` (see note above)."""
    return min(legs, key=lambda leg: deviation_from_straight(probes, center, point, leg))


# The forward leg is the through leg: from OSM tags if they tell (see through_leg_from_osm_tags()) - in a curve, it may
# well be the less straight one -, else from geometry (see through_leg_from_geometry()). If the tags contradict a
# clear geometry (one leg straighter by more than CLEAR_ANGLE_DIFFERENCE), either is probably wrong in OSM: logged as
# a warning, the tags still win. The diverging leg branches off to the right if it lies clockwise of the forward leg
# (seen from the switch, in the projected CRS with x east and y north), i.e. it's a right switch - otherwise to the
# left.
def switch_legs(graph: nx.MultiDiGraph | nx.DiGraph, switch: int, point: int, distance: float = DISTANCE) -> tuple[int, int, bool]:
    """Return `(forward_leg, diverging_leg, diverges_right)` when passing `switch` from `point` into its legs - the
    through leg from OSM tags, else from geometry (see note above).

    Caveat: the `service`/`ref` rule of `through_leg_from_osm_tags` can be misled by incomplete tags. E.g. at switch
    [1338901961](https://www.openstreetmap.org/node/1338901961) (in `download_rail_graph("Walenstadt", dist=15000)`),
    on the map, way 497863617 goes straight on and way 119090347 diverges to the left - but as way 497863617 lacks
    `ref=884`, the tags make way 119090347 the through leg, so the switch is taken as a right one (warned about):

    | Track                    | Way                                                    | Next node                                                | Tags                         | From straight |
    |--------------------------|--------------------------------------------------------|----------------------------------------------------------|------------------------------|---------------|
    | point                    | [119090386](https://www.openstreetmap.org/way/119090386) | [1338901980](https://www.openstreetmap.org/node/1338901980) | `service=yard`, `ref=884`    | -             |
    | through leg by the tags  | [119090347](https://www.openstreetmap.org/way/119090347) | [1338901959](https://www.openstreetmap.org/node/1338901959) | `service=yard`, `ref=884`    | 5.9 degrees   |
    | through leg on the map   | [497863617](https://www.openstreetmap.org/way/497863617) | [1339651418](https://www.openstreetmap.org/node/1339651418) | `service=yard`               | 0.8 degrees   |

    Future refinement: let a clear geometry (one leg straighter by more than `CLEAR_ANGLE_DIFFERENCE`) override the
    `service`/`ref` rule, keeping way continuity (`osmid`) first - this would get the switch above right, and changes
    nothing for the 8 switches tagged with `railway:turnout_side` checked so far (whose legs differ by less)."""
    probes = switch_probes(graph, switch, distance)
    center = Point(graph.nodes[switch]["x"], graph.nodes[switch]["y"])
    legs = [neighbour for neighbour in probes if neighbour != point]
    assert len(legs) == 2, f"switch {switch} with point {point} has legs {legs}"
    from_geometry = through_leg_from_geometry(probes, center, point, legs)
    forward = through_leg_from_osm_tags(graph, switch, point, legs)
    if forward is None:
        forward = from_geometry
    elif forward != from_geometry:
        difference = abs(deviation_from_straight(probes, center, point, legs[0])
                         - deviation_from_straight(probes, center, point, legs[1]))
        if difference > CLEAR_ANGLE_DIFFERENCE:
            logger.warning(f"switch {switch}: OSM tags make {forward} the through leg, but {from_geometry} is "
                           f"{difference:.1f} degrees straighter - taking {forward}")
    diverging = next(leg for leg in legs if leg != forward)
    f, d = probes[forward], probes[diverging]
    cross = (f.x - center.x) * (d.y - center.y) - (f.y - center.y) * (d.x - center.x)
    return forward, diverging, cross < 0
