"""Where a vertex or a train of a graph rail env (see `double_vertex_graph_to_env.create_env`) is on the map, as
(lat, lon) - the graph's coordinates are the OSM nodes' (`x` = lon, `y` = lat, as osmnx), there is no grid
representation.

Both vertices of a track node, `"x"` and `"x_prime"`, are at the track node. A train between two vertices is placed
along its edge's geometry (the OSM way's shape), at its offset on the edge (distance / edge length).
"""
import math

import networkx as nx
from flatland.envs.graph_rail_env import GraphRailEnv
from shapely.geometry import LineString

from switch_geometry import oriented_geometry


def vertex_lat_lon(g: nx.DiGraph, vertex: str) -> tuple[float, float]:
    """(lat, lon) of `vertex` of the double vertex graph `g`."""
    return g.nodes[vertex]["y"], g.nodes[vertex]["x"]


def edge_point_lat_lon(g: nx.DiGraph, u: str, v: str, fraction: float) -> tuple[float, float]:
    """(lat, lon) at `fraction` (0: `u`, 1: `v`) of the length of edge (u, v) of `g`, along its geometry (the straight
    segment if it has none).

    The geometry is in lon/lat degrees: lon is scaled by cos(lat) to measure lengths along it (a local equirectangular
    approximation, exact enough for the length of an edge)."""
    geom = oriented_geometry(g, u, v, None, u)
    scale = math.cos(math.radians(geom.coords[0][1]))
    scaled = LineString([(x * scale, y) for x, y in geom.coords])
    point = scaled.interpolate(fraction, normalized=True)
    return point.y, point.x / scale


def position_lat_lon(env: GraphRailEnv, handle: int) -> tuple[float, float] | None:
    """(lat, lon) of train `handle` of `env`: on its edge from the current to the next entry point, at its offset;
    at its current entry point if it is not on an edge; None if it is not on the map."""
    agent = env.agents[handle]
    u, v = agent.current_entry_point, agent.next_entry_point
    if u is None:
        return None
    if v is None or agent.speed_counter.distance is None:
        return vertex_lat_lon(env.rail.g, u)
    fraction = float(agent.speed_counter.distance / agent.speed_counter.edge_length)
    return edge_point_lat_lon(env.rail.g, u, v, fraction)
