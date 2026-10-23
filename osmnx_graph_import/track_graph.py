"""Load a track graph preprocessed by `osm_to_track_graph.download_rail_graph_fixed` from GraphML and convert it to its double
vertex graph (the input of the conversion to a GraphRailEnv).

* Track graph: one node per OSM node (switches, buffer stops, ends of ways), one edge per piece of physical track. Edge
  directions are only the OSM ways' drawing directions, they say nothing about the direction of travel.
* Double vertex graph: two vertices per track node, one per side of its tracks, and one directed edge per possible
  movement of a train, see M. Montigel: Formal representation of track topologies by double vertex graphs. In:
  Computers in Railways III (COMPRAIL 92), vol. 2, Computational Mechanics Publications, 1992, pp. 359-370.
"""
from pathlib import Path

import networkx as nx
import osmnx as ox
from osmnx.simplification import _get_paths_to_simplify

from osm_to_track_graph import true_switches
from switch_geometry import legs_from_geometry


def load_track_graph(filepath: str | Path) -> nx.DiGraph:
    """Load the track graph saved at `filepath` (see `osm_to_track_graph.download_rail_graph_fixed`) and verify it.

    The GraphML file is technically a MultiDiGraph (as osmnx saves and loads it), but must semantically be a
    DiGraph - it is returned as such. A switch is a node with in+out degree > 2 (see `osm_to_track_graph.true_switches`).
    Raises `ValueError` on the first check that fails:

    | # | Check                                                                                    | Why                                                                                                                                                         |
    |---|------------------------------------------------------------------------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------|
    | 1 | No parallel edges: one key per `(u, v)`                                                  | Converting to a DiGraph would merge parallel edges (two tracks between the same pair of nodes).                                                            |
    | 2 | No self-loops, no edge in both directions (`u -> v` and `v -> u`)                        | `to_undirected()` (used by the GraphRailEnv conversion) would merge such edges.                                                                             |
    | 3 | Every node has in+out degree <= 3                                                        | A switch has exactly one point and two legs.                                                                                                                |
    | 4 | Every switch has the OSM tag `railway=switch`                                            | Consistency of the OSM tags with the topology (see the comment in the code).                                                                                |
    | 5 | No interstitial nodes, except a single one between two switches                         | The graph is simplified; `simplify_graph_keep_switch_intermediate` keeps one interstitial node between two switches on purpose.                            |
    | 6 | Every node has coordinates `x`, `y`; every edge has a `length` > 0                       | Switch geometry (left/right, closest legs) and edge lengths in metres.                                                                                      |
    """
    G = ox.io.load_graphml(filepath=filepath)

    # 1
    parallel_edges = [(u, v) for u, v in set(G.edges()) if G.number_of_edges(u, v) > 1]
    if parallel_edges:
        raise ValueError(f"parallel edges: {parallel_edges}")

    # 2
    self_loops = list(nx.selfloop_edges(G))
    if self_loops:
        raise ValueError(f"self-loops: {self_loops}")
    antiparallel_edges = [(u, v) for u, v in G.edges() if G.has_edge(v, u)]
    if antiparallel_edges:
        raise ValueError(f"edges in both directions: {antiparallel_edges}")

    # 3
    over_degree = {n: G.in_degree(n) + G.out_degree(n) for n in G.nodes if G.in_degree(n) + G.out_degree(n) > 3}
    if over_degree:
        raise ValueError(f"node(s) with in+out degree > 3: {over_degree}")

    # 4
    # N.B. this checks the OSM tagging, not the topology, and might fail for other places than the ones we have looked
    # at so far - we might come back to the decision to fail here (instead of e.g. just warning).
    switches = true_switches(G)
    missing_switch_tag = [n for n in switches if G.nodes[n].get("railway") != "switch"]
    if missing_switch_tag:
        raise ValueError(f"node(s) with in+out degree > 2 but no railway=switch tag: {missing_switch_tag}")

    # 5
    # osmnx's own endpoint/path-building logic (see simplify_graph's source) yields every path it would still
    # collapse - only switch -> kept interstitial node -> switch may be left
    interstitial_paths = [
        path for path in _get_paths_to_simplify(G, None, None)
        if not (len(path) == 3 and path[0] in switches and path[-1] in switches)
    ]
    if interstitial_paths:
        raise ValueError(f"interstitial node(s) on path(s): {interstitial_paths}")

    # 6
    missing_coordinates = [n for n, d in G.nodes(data=True) if "x" not in d or "y" not in d]
    if missing_coordinates:
        raise ValueError(f"node(s) without coordinates: {missing_coordinates}")
    bad_lengths = [(u, v) for u, v, length in G.edges(data="length") if length is None or not length > 0]
    if bad_lengths:
        raise ValueError(f"edge(s) without a length > 0: {bad_lengths}")

    return nx.DiGraph(G)


PRIME_SUFFIX = "_prime"


def opposite_vertex(vertex: str) -> str:
    """The other vertex of `vertex`'s track node: toggle between "x" and "x_prime"."""
    return vertex.removesuffix(PRIME_SUFFIX) if vertex.endswith(PRIME_SUFFIX) else f"{vertex}{PRIME_SUFFIX}"


def track_node(vertex: str) -> int:
    """Track node of the double vertex graph's vertex "x" / "x_prime"."""
    return int(vertex.removesuffix(PRIME_SUFFIX))


def track_sides(track_graph: nx.DiGraph, track_graph_proj: nx.MultiDiGraph | nx.DiGraph) -> dict[int, dict[int, int]]:
    """Side (0 or 1) of every node's tracks, per node and neighbour: a train passing a node enters from one side and
    leaves to the other. At a switch, its legs (see `switch_geometry.legs_from_geometry`) are on side 0 and its point on
    side 1; any other node has its first track (out-edges before in-edges, i.e. along the OSM way's direction for a
    node with one of each) on side 0 and its second track, if any, on side 1. `track_graph_proj` is `track_graph`
    projected to a metric CRS."""
    sides = {}
    for n in track_graph.nodes:
        neighbors = list(track_graph.successors(n)) + list(track_graph.predecessors(n))
        if len(neighbors) == 3:
            legs = set(legs_from_geometry(track_graph_proj, n))
            sides[n] = {nb: 0 if nb in legs else 1 for nb in neighbors}
        else:
            sides[n] = {nb: side for side, nb in enumerate(neighbors)}
    return sides


def build_double_vertex_graph(track_graph: nx.DiGraph) -> nx.DiGraph:
    """Double vertex graph (see Montigel in the module docstring) of `track_graph` (as loaded by `load_track_graph`), in
    which trains can only move along edges.

    Every track node `x` becomes two vertices - `"x"`: the train leaves `x` to side 0 of its tracks, `"x_prime"`: it
    leaves `x` to side 1 (see `track_sides`). Every track `u - v` becomes two edges, one per direction of travel: leaving
    `u` to the side facing `v`, the train enters `v` from the side facing `u` and so leaves `v` to the other side. Node
    and edge attributes are copied from `track_graph`.

    | Guarantee                                                                                                | Why                                                                                                                                  |
    |----------------------------------------------------------------------------------------------------------|--------------------------------------------------------------------------------------------------------------------------------------|
    | Never fails on a graph from `load_track_graph`, terminates in O(edges)                                   | Each node's sides are decided locally from its own tracks, each track is visited once - nothing is propagated, so nothing conflicts. |
    | Deterministic                                                                                            | Sides depend only on `track_graph`'s node/edge order and geometry.                                                                   |
    | Edge duality: `a -> b` iff `opposite_vertex(b) -> opposite_vertex(a)`                                    | The two edges of a track are each other's dual.                                                                                      |
    | Every path in `track_graph` that never passes a switch leg to leg is a path here, and vice versa         | Entering a node from one side, the train can only leave to the other: at a switch, from its point to either leg or back.             |
    | Reversing loops (balloon loops, wyes) are supported                                                      | They connect `"x"` and `"x_prime"` - the train comes back to `x` facing the other way.                                               |
    | A dead end `x`: `"x_prime"` has no outgoing edge                                                         | Its side 1 has no track.                                                                                                             |
    """
    track_graph_proj = ox.projection.project_graph(nx.MultiDiGraph(track_graph))
    sides = track_sides(track_graph, track_graph_proj)

    def vertex(n: int, side: int) -> str:
        return str(n) if side == 0 else f"{n}{PRIME_SUFFIX}"

    double_vertex_graph = nx.DiGraph()
    double_vertex_graph.graph.update(track_graph.graph)
    for n, data in track_graph.nodes(data=True):
        double_vertex_graph.add_node(vertex(n, 0), **data)
        double_vertex_graph.add_node(vertex(n, 1), **data)
    for u, v, data in track_graph.edges(data=True):
        for a, b in ((u, v), (v, u)):
            double_vertex_graph.add_edge(vertex(a, sides[a][b]), vertex(b, 1 - sides[b][a]), **data)
    return double_vertex_graph
