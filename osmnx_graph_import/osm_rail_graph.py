"""Download the railway graph of an OSM place with OSMnx, keeping one node between adjacent switches.

`download_rail_graph_fixed` downloads the non-simplified railway graph for a place, either within the place's
boundary or within a radius around it, simplifies it with `simplify_graph_keep_switch_intermediate`, and either
returns the result or also saves it to a GraphML file.
"""
import itertools
from collections.abc import Callable
from pathlib import Path

import networkx as nx
import osmnx as ox
from osmnx.simplification import _get_paths_to_simplify
from shapely import LineString, Point

RAILWAY_FILTER = '["railway"~"rail"]'


def download_rail_graph(
    place: str,
    dist: float | None = None,
    simplify: bool = True,
    custom_filter: str = RAILWAY_FILTER,
) -> nx.MultiDiGraph:
    """Download the railway graph of `place` from OSM.

    Without `dist`, the graph is limited to the place's boundary polygon (`ox.graph.graph_from_place`). With
    `dist`, `place` is geocoded to a point and the graph is limited to the bounding box `dist` metres around it
    (`ox.graph.graph_from_address`).

    Every OSM way becomes a single directed edge in OSM node order (`ox.settings.all_oneway = True`, restored
    afterwards). Only the largest weakly connected component is kept, and nodes outside the boundary are kept
    if one of their neighbours lies within it.
    """
    all_oneway = ox.settings.all_oneway
    ox.settings.all_oneway = True
    try:
        kwargs = dict(
            retain_all=False,  # only the largest weakly connected component
            truncate_by_edge=True,  # keep nodes outside the boundary if one of their neighbours lies within it
            simplify=simplify,
            custom_filter=custom_filter,
        )
        if dist is None:
            return ox.graph.graph_from_place(place, **kwargs)
        return ox.graph.graph_from_address(place, dist=dist, **kwargs)
    finally:
        ox.settings.all_oneway = all_oneway


def true_switches(G: nx.MultiDiGraph) -> set[int]:
    """Nodes with in+out degree > 2 - a node's OSM railway=switch tag can lag behind the actual topology."""
    return {n for n in G.nodes if G.in_degree(n) + G.out_degree(n) > 2}


# Custom simplification: identical to osmnx.simplification.simplify_graph (see
# its source - _is_endpoint/_get_paths_to_simplify/_build_path determine the
# endpoints and interstitial paths; simplify_graph then aggregates each path's
# edge attributes - summing "length"/"travel_time", keeping a single value
# where all segments agree, else keeping the list of unique values - and
# builds the merged edge's `geometry` from every node's coordinates along the
# path), EXCEPT: whenever a path's two endpoints are both switches and it has
# at least one interstitial node, that node is kept instead of removed, and
# the path is built as two edges (through that node) instead of one - using
# the exact same per-path attribute-aggregation/geometry logic, just applied
# to each half separately.
# NOTE: this does not guarantee an intermediate node survives between every
# pair of switches - if two switches are already directly adjacent in the
# non-simplified graph (0 interstitial nodes for that path), there is nothing
# to keep, and the switch-switch edge remains direct. Whether that happens is
# purely a property of the OSM data (how finely the way was split), not
# something this function controls.
def simplify_graph_keep_switch_intermediate(
    G: nx.MultiDiGraph,
    switch_osmids: set[int],
    edge_attr_aggs: dict[str, Callable] | None = None,
) -> nx.MultiDiGraph:
    """Like osmnx.simplification.simplify_graph, but keeps one interstitial
    node on every switch-switch path (see note above)."""
    if G.graph.get("simplified"):
        raise ValueError("This graph has already been simplified, cannot simplify it again.")
    if edge_attr_aggs is None:
        edge_attr_aggs = {"length": sum, "travel_time": sum}

    G = G.copy()

    def path_edge_attrs(path: list[int]) -> dict:
        """Aggregate one interstitial path's edge attributes and geometry."""
        path_attributes = {}
        for u, v in itertools.pairwise(path):
            edge_data = next(iter(G.get_edge_data(u, v).values()))
            for attr, value in edge_data.items():
                path_attributes.setdefault(attr, []).append(value)
        for attr_name, attr_values in path_attributes.items():
            if attr_name in edge_attr_aggs:
                path_attributes[attr_name] = edge_attr_aggs[attr_name](attr_values)
            elif len(set(attr_values)) == 1:
                path_attributes[attr_name] = attr_values[0]
            else:
                path_attributes[attr_name] = list(set(attr_values))
        path_attributes["geometry"] = LineString(
            [Point((G.nodes[n]["x"], G.nodes[n]["y"])) for n in path]
        )
        return path_attributes

    all_nodes_to_remove = []
    all_edges_to_add = []

    for path in _get_paths_to_simplify(G, None, None):
        is_switch_switch = path[0] in switch_osmids and path[-1] in switch_osmids
        if is_switch_switch and len(path) > 2:
            # keep exactly one interstitial node - split the path in two there
            mid_idx = len(path) // 2
            mid_node = path[mid_idx]
            for sub_path in (path[: mid_idx + 1], path[mid_idx:]):
                all_edges_to_add.append({
                    "origin": sub_path[0],
                    "destination": sub_path[-1],
                    "attr_dict": path_edge_attrs(sub_path),
                })
            all_nodes_to_remove.extend(n for n in path[1:-1] if n != mid_node)
        else:
            all_edges_to_add.append({
                "origin": path[0],
                "destination": path[-1],
                "attr_dict": path_edge_attrs(path),
            })
            all_nodes_to_remove.extend(path[1:-1])

    for edge in all_edges_to_add:
        G.add_edge(edge["origin"], edge["destination"], **edge["attr_dict"])
    G.remove_nodes_from(set(all_nodes_to_remove))
    G.graph["simplified"] = True
    return G


def download_rail_graph_fixed(
    place: str,
    dist: float | None = None,
    filepath: str | Path | None = None,
) -> nx.MultiDiGraph:
    """Download the non-simplified railway graph of `place` (see `download_rail_graph`) and simplify it keeping
    one interstitial node between adjacent switches (see `simplify_graph_keep_switch_intermediate`).

    With `filepath`, the result is also saved there as GraphML.
    """
    G_non_simple = download_rail_graph(place, dist=dist, simplify=False)
    # its real branch points still have degree > 2
    G_fixed = simplify_graph_keep_switch_intermediate(G_non_simple, true_switches(G_non_simple))
    if filepath is not None:
        ox.io.save_graphml(G_fixed, filepath=filepath)
    return G_fixed
