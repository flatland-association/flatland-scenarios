import ast
import json
from collections import deque
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


def assert_double_vertex_graph(track_graph: nx.DiGraph, double_vertex_graph: nx.DiGraph):
    """Assert `double_vertex_graph` is a correct double vertex graph of `track_graph`."""
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


@pytest.mark.parametrize("filename", GRAPHS)
def test_build_double_vertex_graph(filename: str):
    track_graph = load_track_graph(DATA_DIR / filename)

    double_vertex_graph = build_double_vertex_graph(track_graph)

    assert_double_vertex_graph(track_graph, double_vertex_graph)


@pytest.mark.parametrize("filename,reversing", GRAPHS.items())
def test_build_double_vertex_graph_reversing_loop(filename: str, reversing: bool):
    double_vertex_graph = build_double_vertex_graph(load_track_graph(DATA_DIR / filename))

    # with a reversing loop, a train can come back to a node facing the other way
    assert any(nx.has_path(double_vertex_graph, v, opposite_vertex(v)) for v in double_vertex_graph.nodes) == reversing


def test_build_double_vertex_graph_deterministic():
    track_graph = load_track_graph(DATA_DIR / "sargans_reversing_loop.graphml")

    assert list(build_double_vertex_graph(track_graph).edges) == list(build_double_vertex_graph(track_graph).edges)


NOTEBOOK = DATA_DIR / "flatland_osmnx_import_pipeline.ipynb"


def notebook_functions(*names: str) -> dict:
    """Functions `names` defined in the notebook's code cells - the notebook's GGG implementations are not part of the
    library, so execute their definitions (only) from the notebook."""
    cells = ["".join(c["source"]) for c in json.loads(NOTEBOOK.read_text())["cells"] if c["cell_type"] == "code"]
    # imported in other cells of the notebook
    namespace = {"nx": nx, "deque": deque, "closest_neighbors": closest_neighbors}
    for name in names:
        (cell,) = [c for c in cells if f"def {name}(" in c]
        tree = ast.parse(cell)
        tree.body = [node for node in tree.body if isinstance(node, (ast.FunctionDef, ast.Import, ast.ImportFrom))]
        exec(compile(tree, str(NOTEBOOK), "exec"), namespace)
    return namespace


def close_neighbor_pairs(track_graph: nx.DiGraph, track_graph_proj: nx.MultiDiGraph) -> dict[int, set[int]]:
    return {s: set(closest_neighbors(track_graph_proj, s)) for s in true_switches(track_graph)}


# TODO fix: the notebook's implementation 2 raises on a reversing loop (and, depending on the graph, completes without
# raising and builds an inconsistent GGG instead) - superseded by build_double_vertex_graph.
@pytest.mark.parametrize("filename", [
    "walensee.graphml",
    pytest.param("sargans_reversing_loop.graphml", marks=pytest.mark.xfail(raises=AssertionError, strict=True, reason="reversing loop")),
])
def test_notebook_build_ggg_impl2(filename: str):
    track_graph = load_track_graph(DATA_DIR / filename)
    track_graph_proj = ox.projection.project_graph(nx.MultiDiGraph(track_graph))
    build_ggg_impl2 = notebook_functions("prime", "build_ggg_impl2")["build_ggg_impl2"]

    double_vertex_graph = build_ggg_impl2(track_graph, close_neighbor_pairs(track_graph, track_graph_proj))

    assert_double_vertex_graph(track_graph, double_vertex_graph)


# TODO fix: the notebook's implementation 3 silently builds an inconsistent GGG on a reversing loop - superseded by
# build_double_vertex_graph.
@pytest.mark.parametrize("filename", [
    "walensee.graphml",
    pytest.param("sargans_reversing_loop.graphml", marks=pytest.mark.xfail(raises=AssertionError, strict=True, reason="reversing loop")),
])
def test_notebook_build_ggg_impl3(filename: str):
    track_graph = load_track_graph(DATA_DIR / filename)
    track_graph_proj = ox.projection.project_graph(nx.MultiDiGraph(track_graph))
    build_ggg_impl3 = notebook_functions("prime", "find_other_neighbor", "build_ggg_impl3")["build_ggg_impl3"]
    # TODO fix: implementation 3 raises ValueError if the first node is a dead end - start at a switch
    switches = true_switches(track_graph)
    ordered = nx.DiGraph()
    ordered.add_nodes_from(sorted(track_graph.nodes(data=True), key=lambda node: node[0] not in switches))
    ordered.add_edges_from(track_graph.edges(data=True))

    double_vertex_graph = build_ggg_impl3(ordered, close_neighbor_pairs(track_graph, track_graph_proj), track_graph_proj)

    assert_double_vertex_graph(track_graph, double_vertex_graph)
