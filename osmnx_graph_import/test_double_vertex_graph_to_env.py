from pathlib import Path

import networkx as nx
import pytest
from flatland.envs.step_utils.states import TrainState

from double_vertex_graph_to_env import create_env, run_shortest_path_policy
from track_graph import build_double_vertex_graph, load_track_graph, opposite_vertex

DATA_DIR = Path(__file__).parent


def test_create_env_walensee(tmp_path: Path):
    track_graph = load_track_graph(DATA_DIR / "walensee.graphml")
    double_vertex_graph = build_double_vertex_graph(track_graph)
    # longest switch-to-switch shortest path: 14 edges, through 7 other switches
    env = create_env(double_vertex_graph, track_graph, source="2042222934", target="2048248489")

    run_shortest_path_policy(env, tmp_path / "shortest_path")

    assert env.agents[0].state == TrainState.DONE


def test_create_env_sargans_reversing_loop(tmp_path: Path):
    track_graph = load_track_graph(DATA_DIR / "sargans_reversing_loop.graphml")
    double_vertex_graph = build_double_vertex_graph(track_graph)
    # come back to the same track node facing the other way - only possible through the reversing loop (not at a dead
    # end, see create_env())
    source = next(v for v in double_vertex_graph.nodes
                  if double_vertex_graph.out_degree(v) > 0 and double_vertex_graph.out_degree(opposite_vertex(v)) > 0
                  and nx.has_path(double_vertex_graph, v, opposite_vertex(v)))
    env = create_env(double_vertex_graph, track_graph, source=source, target=opposite_vertex(source))

    run_shortest_path_policy(env, tmp_path / "shortest_path")

    assert env.agents[0].state == TrainState.DONE


def test_create_env_no_path():
    track_graph = load_track_graph(DATA_DIR / "walensee.graphml")
    double_vertex_graph = build_double_vertex_graph(track_graph)

    with pytest.raises(ValueError, match="no directed path"):
        create_env(double_vertex_graph, track_graph, source="2042222934", target="2042222934_prime")


def test_create_env_dead_end_target():
    track_graph = load_track_graph(DATA_DIR / "sargans_reversing_loop.graphml")
    double_vertex_graph = build_double_vertex_graph(track_graph)

    with pytest.raises(ValueError, match="dead end"):
        create_env(double_vertex_graph, track_graph, source="1195732747", target="1195732747_prime")
