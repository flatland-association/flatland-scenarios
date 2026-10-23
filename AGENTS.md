# AGENTS.md

Scenarios, trajectories and scenario tooling for [Flatland](https://github.com/flatland-association/flatland-rl) - see
`README.md` for what each top-level folder contains (`competitions`, `scenario_generator`, `scenario_olten`,
`scenarios`, `trajectories`) and how the generated scenarios/trajectories are (re-)created.

## Dependencies

There is no `pyproject.toml`/`requirements.txt`: flatland-rl (and, for some parts, flatland-baselines) is installed
from git. CI (`.github/workflows/checks.yml`) pins both to the refs marked `# DEPENDENCY SWITCH` (currently `v4.3.0`).

`osmnx_graph_import` is the exception: it needs flatland-rl's branch `526-edge-lengths` (TODO: main, then a release,
once merged), plus osmnx etc. - its dependencies are listed in the first code cell of
`osmnx_graph_import/flatland_osmnx_import_pipeline.ipynb`. It is not run in CI.

## Tests

Run pytest from the repository root: tests use paths relative to it (e.g. `./scenario_olten/data/...`) and import
`competitions`/`scenario_generator` as packages (the root has an `__init__.py`).

```shell
pytest -s scenario_generator
pytest -s competitions
# scenario_olten verifies the trajectories written by executing its notebook first:
PYTHONPATH=$PWD/../flatland-baselines python -m jupyter nbconvert --ExecutePreprocessor.timeout=600 --execute --to notebook --inplace scenario_olten/scenario_olten.ipynb
pytest -s scenario_olten
pytest osmnx_graph_import  # test_double_vertex_graph_to_env.py needs flatland-rl branch 526-edge-lengths
# single test
pytest "osmnx_graph_import/test_track_graph.py::test_build_double_vertex_graph[walensee.graphml]"
```

## osmnx_graph_import: OSM railway data -> GraphRailEnv

A pipeline of three flat modules (no package: they import each other by module name, the notebook and the tests run
from that folder, pytest puts it on the path):

1. `osm_to_track_graph.py`: download the OSM railway network of a place (boundary, or radius around it) with osmnx,
   simplified like `osmnx.simplify_graph` but keeping one interstitial node between two adjacent switches; optionally
   saved as GraphML.
2. `track_graph.py`: `load_track_graph` loads such a GraphML file and verifies it (table of checks in its docstring),
   returning a DiGraph: one node per OSM node, one edge per piece of track, edge direction meaningless for travel.
   `build_double_vertex_graph` converts it to a double vertex graph (Montigel, COMPRAIL 92): vertices `"x"` / `"x_prime"`
   per track node (leaving it to side 0 / side 1 of its tracks), one edge per possible train movement. The side-based
   construction is local, deterministic and supports reversing loops (balloon loops, wyes), which connect `"x"` and
   `"x_prime"`.
3. `double_vertex_graph_to_env.py`: rail env actions partitioned per vertex, resource map, edge lengths as `Fraction`s
   (flatland rejects floats), a single-train `GraphRailEnv` from source to target vertex, and
   `GraphShortestPathPolicy`. A target without outgoing edge (dead end) is rejected: flatland's `step()` fails there.

`switch_geometry.py` decides a switch's legs from geometry (the two tracks that stay closest, probed 10 m from the
switch on the projected graph), and its through leg - from OSM tags first (the leg continuing the point's way, else the
only one with the point's `service`/`ref`), else from geometry (the straighter leg) - and so whether it diverges left or
right. A warning is logged when the tags contradict a clear geometry; see the caveat in `switch_legs`.

The osmnx_graph_import tests must not download anything: they use the committed GraphML files or hard-coded OSM data
(e.g. `test_switch_geometry.py`). Live downloads (notebook, `osm_to_track_graph`) go through osmnx's cache in `./cache`
and the public Overpass API, which rate-limits heavy use.

The notebook is the exploration around this pipeline: it calls the modules, and still contains the earlier GGG
construction attempts (implementations 1-3, marked `TODO fix`, superseded) - `GG`/`GGG` are notebook names only, the
library says track graph / double vertex graph. Test fixtures: `walensee.graphml` (Walenstadt, no reversing loop) and
`sargans_reversing_loop.graphml` (a reversing loop, on which implementations 2 and 3 fail - `xfail` tests in
`test_track_graph.py`).

## Git

- Always commit Jupyter notebooks (`.ipynb`) without outputs: every code cell with empty `outputs` and
  `"execution_count": null`. Keep the outputs in the working copy - stage a stripped copy instead, e.g.:

  ```shell
  sha=$(python3 -c '
  import json, sys
  nb = json.load(open(sys.argv[1]))
  for c in nb["cells"]:
      if c["cell_type"] == "code":
          c["outputs"], c["execution_count"] = [], None
  sys.stdout.write(json.dumps(nb, indent=1, ensure_ascii=False) + "\n")
  ' "$NB" | git hash-object -w --stdin)
  git update-index --cacheinfo 100644,"$sha","$NB"
  ```
