"""Load a railway graph preprocessed by `osm_rail_graph.download_rail_graph_fixed` from GraphML, for the conversion
to a GraphRailEnv."""
from pathlib import Path

import networkx as nx
import osmnx as ox
from osmnx.simplification import _get_paths_to_simplify

from osm_rail_graph import true_switches


def load_rail_graph(filepath: str | Path) -> nx.DiGraph:
    """Load the railway graph saved at `filepath` (see `osm_rail_graph.download_rail_graph_fixed`) and verify it.

    The GraphML file is technically a MultiDiGraph (as osmnx saves and loads it), but must semantically be a
    DiGraph - it is returned as such. A switch is a node with in+out degree > 2 (see `osm_rail_graph.true_switches`).
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
