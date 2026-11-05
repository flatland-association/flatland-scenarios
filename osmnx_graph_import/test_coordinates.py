from pathlib import Path

import pytest
from shapely.geometry import LineString, Point

from coordinates import edge_point_lat_lon, position_lat_lon, vertex_lat_lon
from double_vertex_graph_to_env import GraphShortestPathPolicy, create_env
from switch_geometry import oriented_geometry
from track_graph import build_double_vertex_graph, load_track_graph, opposite_vertex, track_node

DATA_DIR = Path(__file__).parent
# 1e-9 degrees: about 0.1 mm
EPS = 1e-9


@pytest.fixture(scope="module")
def walensee():
    track_graph = load_track_graph(DATA_DIR / "walensee.graphml")
    double_vertex_graph = build_double_vertex_graph(track_graph)
    env = create_env(double_vertex_graph, track_graph, source="2042222934", target="2048248489")
    return track_graph, env


def test_vertex_lat_lon(walensee):
    """The env's graph keeps the OSM coordinates: both vertices of a track node are at the OSM node."""
    track_graph, env = walensee
    for vertex in env.rail.g.nodes:
        node = track_graph.nodes[track_node(vertex)]
        assert vertex_lat_lon(env.rail.g, vertex) == (node["y"], node["x"])
        assert vertex_lat_lon(env.rail.g, opposite_vertex(vertex)) == vertex_lat_lon(env.rail.g, vertex)


def test_edge_point_lat_lon_ends(walensee):
    """At fraction 0, a point on an edge is at its source vertex, at fraction 1 at its target - for every edge, so in
    both directions of travel on each track."""
    _, env = walensee
    g = env.rail.g
    for u, v in g.edges:
        assert edge_point_lat_lon(g, u, v, 0) == pytest.approx(vertex_lat_lon(g, u), abs=EPS)
        assert edge_point_lat_lon(g, u, v, 1) == pytest.approx(vertex_lat_lon(g, v), abs=EPS)


def test_edge_point_lat_lon_follows_curve(walensee):
    """Halfway along the most curved edge, the point lies on the edge's geometry, not on the straight segment between
    its vertices."""
    _, env = walensee
    g = env.rail.g

    def bulge(edge):
        u, v = edge
        chord = LineString([vertex_lat_lon(g, u)[::-1], vertex_lat_lon(g, v)[::-1]])
        return oriented_geometry(g, u, v, None, u).interpolate(0.5, normalized=True).distance(chord)

    u, v = max(g.edges, key=bulge)
    lat, lon = edge_point_lat_lon(g, u, v, 0.5)
    chord = LineString([vertex_lat_lon(g, u)[::-1], vertex_lat_lon(g, v)[::-1]])

    assert Point(lon, lat).distance(oriented_geometry(g, u, v, None, u)) < EPS
    assert Point(lon, lat).distance(chord) > 1e-5  # about 1 m


def test_position_lat_lon(walensee):
    """Through an episode with the shortest-path policy, the train is always on its edge's geometry - None only
    before it enters and after it arrives."""
    _, env = walensee
    observations, _ = env.reset()
    policy = GraphShortestPathPolicy()
    handles = env.get_agent_handles()
    on_edge = 0
    for _ in range(env._max_episode_steps):
        observations, _, dones, _ = env.step(policy.act_many(handles, [observations[h] for h in handles]))
        agent = env.agents[0]
        position = position_lat_lon(env, 0)
        if agent.current_entry_point is None:
            assert position is None
        elif agent.speed_counter.distance is not None:
            lat, lon = position
            u, v = agent.current_entry_point, agent.next_entry_point
            assert Point(lon, lat).distance(oriented_geometry(env.rail.g, u, v, None, u)) < EPS
            on_edge += 1
        if dones["__all__"]:
            break
    assert dones["__all__"]
    assert on_edge > 0
