from pathlib import Path

import networkx as nx
import osmnx as ox
import pytest

from osm_to_track_graph import true_switches
from switch_geometry import closest_neighbors
from track_graph import build_double_vertex_graph, load_track_graph, opposite_vertex, track_node

DATA_DIR = Path(__file__).parent

# walensee.graphml: Walenstadt (download_rail_graph_fixed("Walenstadt")), no reversing loop.
# sargans_reversing_loop.graphml: a reversing loop around Sargans (from download_rail_graph("Walenstadt", dist=15000)),
# with all tracks attached to it - the notebook's implementation 2 raises on it, implementation 3 builds an
# inconsistent GGG.
GRAPHS = {"walensee.graphml": False, "sargans_reversing_loop.graphml": True}


def valid_moves(track_graph: nx.DiGraph) -> set[tuple[int, int, int]]:
    """All (a, b, c) such that a train can go from a via b to c: not leg to leg through a switch b."""
    track_graph_proj = ox.projection.project_graph(nx.MultiDiGraph(track_graph))
    undirected = track_graph.to_undirected()
    switches = true_switches(track_graph)
    moves = set()
    for b in undirected.nodes:
        legs = set(closest_neighbors(track_graph_proj, b)) if b in switches else None
        for a in undirected.neighbors(b):
            for c in undirected.neighbors(b):
                if a != c and {a, c} != legs:
                    moves.add((a, b, c))
    return moves


@pytest.mark.parametrize("filename", GRAPHS)
def test_build_double_vertex_graph(filename: str):
    track_graph = load_track_graph(DATA_DIR / filename)

    double_vertex_graph = build_double_vertex_graph(track_graph)

    assert double_vertex_graph.number_of_nodes() == 2 * track_graph.number_of_nodes()
    assert double_vertex_graph.number_of_edges() == 2 * track_graph.number_of_edges()
    # edge duality
    for a, b in double_vertex_graph.edges:
        assert double_vertex_graph.has_edge(opposite_vertex(b), opposite_vertex(a)), (a, b)
    # every edge is a track
    for a, b in double_vertex_graph.edges:
        assert track_graph.has_edge(track_node(a), track_node(b)) or track_graph.has_edge(track_node(b), track_node(a)), (a, b)
    # the double vertex graph has exactly the valid moves of the track graph - as each direction of a track is a single
    # edge, it follows that every track graph path made of valid moves is a double vertex graph path, and vice versa
    moves = {(track_node(a), track_node(b), track_node(c)) for a, b in double_vertex_graph.edges for c in double_vertex_graph.successors(b)}
    assert moves == valid_moves(track_graph)


@pytest.mark.parametrize("filename,reversing", GRAPHS.items())
def test_build_double_vertex_graph_reversing_loop(filename: str, reversing: bool):
    double_vertex_graph = build_double_vertex_graph(load_track_graph(DATA_DIR / filename))

    # with a reversing loop, a train can come back to a node facing the other way
    assert any(nx.has_path(double_vertex_graph, v, opposite_vertex(v)) for v in double_vertex_graph.nodes) == reversing


def test_build_double_vertex_graph_deterministic():
    track_graph = load_track_graph(DATA_DIR / "sargans_reversing_loop.graphml")

    assert list(build_double_vertex_graph(track_graph).edges) == list(build_double_vertex_graph(track_graph).edges)
