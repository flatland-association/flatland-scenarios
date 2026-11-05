# Plan: OSM import as graph for the Travel Wise dummy scenario

PR [#36](https://github.com/flatland-association/flatland-scenarios/pull/36), branch `feature/osmnx-to-graph-import`,
based on `main` 2e20db2, head c2bc7b4 (44 commits). Closes
[#29](https://github.com/flatland-association/flatland-scenarios/issues/29) ("Travel Wise dummy scenario: import OSM
as graph and grid representation", Bologna simplified: import OSM data; assign lat/lon coordinates to grid and graph
coordinates). Status of 2026-11-04: phase 0 (the pipeline on Walenstadt and Sargans) done, phases 1-3 planned.

The PR imports the OSM railway network of a place into a `GraphRailEnv` that only allows the movements possible on the
real tracks. To close #29 it still has to fail clearly on topologies it cannot represent, and expose the OSM
coordinates of the graph; there is no grid representation (Q3). The Bologna extent itself, the Travel Wise "regional
airport" scenario (flatland-book
[`resources/travelwise.md`](https://github.com/flatland-association/flatland-book/blob/main/resources/travelwise.md)),
is imported with its timetables in #30 (Q1). The open items of the PR's "Remaining" table are either planned here
(phases 1 and 3) or follow-ups.

## Goal

- The pipeline (download, verify, double vertex graph, `GraphRailEnv`) imports OSM data of a place (issue item 1,
  done in phase 0); the Bologna extent and its fixture follow in #30 (Q1).
- It fails verbosely where it cannot represent the topology (nodes of degree > 3) or where the switch legs are
  doubtful, instead of building a wrong graph (phase 1, finding 10).
- Every vertex of the graph rail env, and every train position on an edge, maps to lat/lon (phase 2, issue item 2;
  graph only, no grid: Q3).
- Cleanup: the notebook's superseded implementations dropped, a requirements file, flatland-rl `main` once
  [rl#542](https://github.com/flatland-association/flatland-rl/pull/542) is merged, the offline tests in CI again (phase 3).

## Status

| Phase | ID | Commit message | Status |
|---|---|---|---|
| 0 ✅ | - | 44 commits, 89430c9 .. c2bc7b4, see the PR's "Carried out" table | done |
| 1 ✅ | C1.1 ✅ | `fix: let a clear switch geometry override the OSM service/ref rule.` | 17ff603 |
| 1 ✅ | C1.2 ✅ | `feat: name the OSM node type of nodes with degree > 3 in the track graph verification.` | b4d2dc3 |
| 1 ✅ | C1.3 | `feat: add the simplified Bologna track graph (airport monorail and Bologna Centrale) as a test fixture.` | moved to #30 (Q1) |
| 2 ✅ | C2.1 ✅ | `feat: map the vertices and train positions of the graph rail env to lat/lon.` | 490ecd0 |
| 2 ✅ | C2.2 | `feat: assign grid cells to the vertices of the double vertex graph.` | dropped (Q3) |
| 3 | C3.1 ✅ | `refactor: drop the superseded GGG implementations from the notebook.` | 269ccca |
| 3 | C3.2 ✅ | `fix: color GGG nodes by switch category in explore_categorized.` | 0295bd3 |
| 3 | C3.3 ✅ | `chore: add requirements for the osmnx graph import and run its tests in CI again.` | 1a0c73c |
| 3 | C3.4 | `chore: depend on flatland-rl main for the osmnx graph import.` | blocked by rl#542 |

The steps are independent of each other, except C3.4: it needs C3.3 (the requirements file and the CI job) and is
blocked by [rl#542](https://github.com/flatland-association/flatland-rl/pull/542).

## Design principles

- A pipeline of flat modules, one step each (download, verify, convert, env), each testable on its own. The notebook
  explores; the modules are the library (AGENTS.md, "osmnx_graph_import").
- Fail loudly on what the conversion cannot represent (degree > 3, switches without tag, interstitial nodes); never
  guess silently; the extent is cut around such nodes instead (Q2). Doubtful but representable cases (tags
  contradicting geometry) warn.
- Tests are offline: committed GraphML fixtures or hard-coded OSM data. Live downloads only in the notebook and in
  `osm_to_track_graph`, through osmnx's cache. So CI runs the tests, not the notebook (Q4).
- The import keeps its own dependencies, in its own folder (Q4).
- The graph is the primary representation. Coordinates are node attributes (`x` = lon, `y` = lat, as osmnx), carried
  unchanged from the track graph to the double vertex graph and the env. There is no grid representation (Q3).
- Real units: edge lengths in metres, as `Fraction`s (flatland rejects floats); scaling for display is the notebook's
  business.

Reused concepts:

| Need | Reused concept | Instead of |
|---|---|---|
| Download, simplify, save, load | osmnx (`graph_from_place`, `simplify_graph`'s path logic, GraphML) | own Overpass queries and file format |
| Topology with only possible movements | Montigel's double vertex graph | a node per track node with turn restrictions |
| Env on the graph | `GraphRailEnv.from_graph` with a resource map | a grid `RailEnv` |
| Switch actions | `RailEnvActions`, checked with `GraphTransitionMap._assert_actions_partitioned()` | new graph actions |
| Coordinates of a vertex | the osmnx node attributes `x`, `y` | a separate coordinate table |
| Position on an edge | `switch_geometry.oriented_geometry` (the edge's `geometry` starting at a given node, the straight segment if it has none) and Shapely's `LineString.interpolate` | the notebook's straight line between the two vertices (`train_location`) |
| Train's offset on an edge | the agent's `speed_counter.distance / speed_counter.edge_length`, as the notebook's `train_location` | an own offset bookkeeping |
| Episode run | flatland's `PolicyRunner` and `Trajectory` | an own loop |

## Terms

| Term (code) | Meaning here, and what it is not |
|---|---|
| track graph (`load_track_graph`, notebook: `GG`) | One node per OSM node (switch, buffer stop, end of a way), one edge per piece of track. Edge directions are OSM drawing directions, not directions of travel. |
| track node | A node of the track graph, keyed by its OSM node id. |
| switch (point, legs, through leg, diverging leg) | A track node of degree 3: the train comes from the point and goes to one of the two legs, or back. The through leg continues the point's way (tags) or is the straighter one (geometry). |
| crossing, double slip | OSM nodes of degree 4 (`railway=railway_crossing`, `railway:switch=double_slip`). Not representable: rejected by design, the extent is cut around them (Q2). |
| double vertex graph (`build_double_vertex_graph`, notebook: `GGG`) | Two vertices per track node, `"x"` and `"x_prime"` (leaving it to side 0 / side 1), one directed edge per possible movement. |
| reversing loop | Balloon loop or wye: connects `"x"` with `"x_prime"`, the train comes back facing the other way. |
| graph rail env (`GraphRailEnv`, `create_env`) | The env on the double vertex graph, one resource per track node. |
| coordinates (`x`, `y`) | lon, lat (WGS84) of a track node, shared by both of its vertices. Not projected metres. |
| simplified Bologna | The extent of the Bologna import, decided in #30 (Q1). Not the whole Bologna railway node. |

## Components

Added by this PR (🟩 added, 🟨 modified):

| Component | Responsibility | Change |
|---|---|---|
| `osm_to_track_graph` | Gets the railway network of a place from OSM, simplified so that every switch keeps its legs. Not for checking it. | 🟩 added: a place's railway network can be downloaded and saved in one call. |
| `track_graph` | Checks an imported network and turns it into the possible train movements, including reversing loops. Not for the env. | 🟩 added: an imported network is checked before use, and trains can only move as on the real tracks. |
| `switch_geometry` | Decides at each switch which leg is the through leg and whether the other one diverges left or right. Not for other node types. | 🟩 added: left and right at switches match the real switch; phase 1 makes clear geometry win over incomplete tags. |
| `double_vertex_graph_to_env` | Builds a graph rail env with one train from the possible movements, and a shortest-path policy to drive it. Not a timetable generator (#30). | 🟩 added: a train can run on an imported network. |
| coordinates (`coordinates.py`, planned) | Tells where a vertex or a train is on the map, in lat/lon. Not a grid representation (Q3). | 🟩 added (phase 2): positions in the env can be shown on a map. |
| GraphML fixtures (`walensee.graphml`, `sargans_reversing_loop.graphml`) | Frozen imports the tests run on, independent of OSM changes and the Overpass API. | 🟩 added: the tests run offline. |
| `flatland_osmnx_import_pipeline.ipynb` | Explores the import step by step on a map, down to stepping a train through an episode. Not tested. | 🟩 added: the import can be inspected and the train watched on a map. |
| requirements (planned) | Lists what the import needs. | 🟩 added (phase 3): the import can be installed without reading the notebook. |
| `.github/workflows/checks.yml` | Runs the repo's tests. | 🟨 modified (phase 3): also runs the offline osmnx tests. |

## Phase 0: the pipeline on Walenstadt and Sargans ✅

89430c9 .. c2bc7b4; details in the PR's "Carried out" table and in AGENTS.md. Download with one interstitial node kept
between adjacent switches; `load_track_graph` with six checks; `build_double_vertex_graph` with a local, side-based
construction supporting reversing loops; switch legs from OSM tags, else geometry, with a warning on contradictions;
`create_env` with partitioned actions, one resource per track node, `Fraction` lengths, dead-end targets rejected;
`GraphShortestPathPolicy`; tests on `walensee.graphml` and `sargans_reversing_loop.graphml`; the notebook with an
interactive step-through.

## Phase 1: other topologies ✅

Goal: on unknown topologies the pipeline fails with a message that says what to fix.

| ID | Finding | Change | Tests |
|---|---|---|---|
| C1.1 ✅ | 22 | `switch_legs`: way continuity (`osmid`) first, then a clear geometry, then the `service`/`ref` rule, as proposed under "Future refinement" in `switch_legs`' docstring. "Clear" is the existing `CLEAR_ANGLE_DIFFERENCE` (5 degrees) of the contradiction warning. | The caveat's switch 1338901961 (its point's next node is 1338901980), its three ways hard-coded from OSM as of 2026-11-04 in `test_switch_geometry.py`, and the test switch with `service`/`ref` tags and a lowered `CLEAR_ANGLE_DIFFERENCE`: both fail before, pass after; the existing tests stay green. |
| C1.2 ✅ | 10 | Check 3 of `load_track_graph` names the OSM tags of each node of degree > 3 (`railway`, `railway:switch`) and links the node on openstreetmap.org, and suggests cutting the extent around it (Q2). No new node types. | A small track graph with a crossing raises `ValueError` naming `railway_crossing`. |
| C1.3 | - | Moved to #30 (Q1): download the simplified Bologna with `download_rail_graph_fixed`, commit it as `bologna_simplified.graphml`, add it to the parametrized tests. `RAILWAY_FILTER` (`"railway"~"rail"`) already matches `monorail` and `light_rail`; check the airport line's tag in OSM first [unverified]. | `load_track_graph`, `build_double_vertex_graph` and `create_env` + `GraphShortestPathPolicy` reaching the target, airport -> Bologna Centrale. |

C1.3 is not in this PR: the Bologna extent is decided with the timetables in #30 (Q1). There, C1.2's messages show where
to cut Bologna Centrale's crossings and double slips.

## Phase 2: coordinates in the graph ✅

Goal: issue item 2 - lat/lon of every vertex and train position. The grid part of the item is dropped (Q3).

| ID | Finding | Change | Tests |
|---|---|---|---|
| C2.1 ✅ | - | `coordinates.py`: `vertex_lat_lon(g, vertex)` from the node attributes `y`, `x`; `position_lat_lon(env, handle)` at the train's offset (`speed_counter.distance / speed_counter.edge_length`) along the edge's geometry, oriented from the current to the next vertex with `switch_geometry.oriented_geometry` (which gets an optional edge key, to work on the env's `DiGraph`). Both read `env.rail.g`, which keeps the attributes (Q6). The notebook's `train_location` (a straight line between the vertices) is replaced by `position_lat_lon`, so the locomotive follows curves. | On Walenstadt: vertex coordinates equal the OSM node's, `"x"` and `"x_prime"` share them; at offset 0 the position is the current vertex, at the edge's length the next one, on an edge in either direction; halfway along a curved edge it lies on the geometry, not on the straight segment. |
| C2.2 | - | Dropped (Q3): no grid representation for the OSM import. | - |

## Phase 3: cleanup and dependencies

| ID | Finding | Change | Tests |
|---|---|---|---|
| C3.1 ✅ | 13, 14, 15 | Drop the notebook's GGG implementations 1-3, their "Results" section and the two `xfail` tests in `test_track_graph.py`, and AGENTS.md's paragraph on them (Q5); the boundary-path and `rstrip` TODOs go with them. | The remaining tests; the notebook runs to the end. |
| C3.2 ✅ | 19 | `explore_categorized` maps a double vertex graph's string vertex to its track node (`track_graph.track_node`) before looking up the switch category. The step-through's `create_map` reuses `track_node` instead of its own copy `gg_node`. | Notebook only (no test for map styling): on Walenstadt, GGG gets 30 switch vertices (both vertices of the 15 switches) instead of 0, GG stays at 15. |
| C3.3 ✅ | 17 | `osmnx_graph_import/requirements.txt` from the notebook's first cell (flatland-rl from branch `526-edge-lengths` until C3.4); the notebook installs from it; AGENTS.md points to it, and no longer says "not run in CI". The job `run-osmnx-graph-import` comes back into `checks.yml`, with the setup of 1a637c8 (ubuntu-22.04, Python 3.13), installing from `requirements.txt` and running `pytest osmnx_graph_import` - offline, not the notebook, which 99d5641 took out of CI after Overpass 502s (Q4). | `pip install -r` into a fresh env, then `pytest osmnx_graph_import`; the new CI job is green. |
| C3.4 | 12 | Once rl#542 is merged: flatland-rl `main` (then a release) in the requirements, the notebook, the module docstring and AGENTS.md "Dependencies"; the CI job of C3.3 picks it up through `requirements.txt`. | The CI job of C3.3. |

Not in phases 1-3: findings 16, 18, 20, 21, 23 - follow-ups, see there.

## Limitations (`create_env`'s and `load_track_graph`'s docstrings, `switch_legs`' caveat, AGENTS.md)

- One train with a hard-coded timetable (follow-up #30, finding 16).
- Nodes of degree > 3 (crossings, double slips) are rejected by design; the extent must be cut around them (Q2, C1.2).
- Incomplete `service`/`ref` tags can still mislead the through leg where the geometry is not clear (legs differing by
  less than `CLEAR_ANGLE_DIFFERENCE`, 5 degrees); way continuity wins also against a clear geometry (warned about).
- A target without outgoing edge is rejected: `GraphRailEnv.step()` fails there (upstream, finding 23).
- No persistence: `run_shortest_path_policy` runs with `no_save=True`; trajectories with graph node ids cannot be read
  back (upstream, findings 20, 21).
- `GraphShortestPathPolicy` takes the path with the fewest edges, not the shortest in metres.
- The notebook stays out of CI (Overpass downloads); only the offline tests run there (C3.3). Needs an unreleased
  flatland-rl branch (C3.4).

## Assumptions

Not checked in code; they hold by construction of the fixtures and of osmnx's output:

- The OSM data of the extent is complete enough: every track is a `railway` way and every switch joins its ways at a
  shared node (checks 3-5 catch the rest).
- One interstitial node between adjacent switches is enough to tell their legs apart.
- `x`/`y` are WGS84 lon/lat and `length` is in metres, as osmnx writes them.
- The committed GraphML fixtures are the reference for the tests; OSM edits after the download do not change them.

## New patterns

Compared with `main`; the reused concepts are listed under the design principles.

| New | Reuses | Defined in |
|---|---|---|
| Real infrastructure imported from OSM, frozen as GraphML fixtures for offline tests | osmnx | Phase 0, AGENTS.md |
| A double vertex graph as the input of `GraphRailEnv` | `GraphRailEnv.from_graph` | Phase 0 |
| Switch actions derived from OSM tags and geometry | `RailEnvActions` | Phase 0, C1.1 |
| Coordinates as node attributes of the env's graph | osmnx node attributes | Phase 2 |
| Notebooks committed without outputs | - | AGENTS.md "Git" |
| A CI job installing from a folder's own requirements file, instead of inline `pip install` | the existing jobs' setup in `checks.yml` | C3.3, Q4 |

Not new on purpose: no change to flatland-rl's API, no package layout (flat modules, as AGENTS.md says), the existing
scenarios and their tests unchanged.

## Breaking changes

None: everything is new under `osmnx_graph_import/`; the existing scenarios are untouched. `checks.yml` gets a new job
in C3.3, the existing jobs stay as they are.

## Follow-ups (not in this PR)

| Follow-up | Why not in this PR | From | Findings | Issue |
|---|---|---|---|---|
| The simplified Bologna (the test file of C1.3) with lines and conflict-free, multi-train timetables. The monorail and the main line at Bologna Centrale are separate components there: trains never change between them, passengers do. | The extent is decided with the timetables (Q1). | C1.3, Limitations | 16 | [#30](https://github.com/flatland-association/flatland-scenarios/issues/30) |
| Snapshot visualization, preferably an osmnx export with railway features. | Needs a `GraphRailEnv` that can be saved (finding 21). | Limitations | 18 | - |
| flatland-rl: read graph node ids in `trains_positions` as strings, with a round-trip test. | Another repo. | Limitations | 20 | - |
| flatland-rl: save (persist) a `GraphRailEnv`, so `run_shortest_path_policy` no longer needs `no_save=True`. | Another repo. | Limitations | 21 | - |
| flatland-rl: let a train end at a dead end, where `GraphRailEnv.step()` fails an assertion. | Another repo. | Limitations | 23 | - |
| Generalized map import: graph only, no grid transform; crossings and double slips stay rejected. | Its own issue (Q2, Q3). | Q2, Q3 | - | [#31](https://github.com/flatland-association/flatland-scenarios/issues/31) |
| Schedules for trains, planes, ships. | Its own issue. | - | - | [#32](https://github.com/flatland-association/flatland-scenarios/issues/32) |
| flatland-rl 5.0.0 for the other scenarios. | Its own issue. | - | - | [#37](https://github.com/flatland-association/flatland-scenarios/issues/37) |

## Open questions

- ✅ ~~**(Q1) Extent of the simplified Bologna.**~~ **Decided 2026-11-04:** for later, in follow-up #30; C1.3 moves
  there. Options to weigh then: a) the airport monorail (Marconi Express) only; b) a) plus the main line platforms of
  Bologna Centrale and the tracks to the first switches outside it, cut where C1.2 reports no degree > 3; c) the
  whole Bologna node (fails on crossings and double slips, Q2).
- ✅ ~~**(Q2) Nodes of degree > 3.**~~ **Decided 2026-11-04:** a) keep rejecting them, with the message of C1.2,
  and cut the extent around them - in this PR and in #31. Not taken: b) split crossings into two unconnected track
  nodes at the same coordinates (only straight movements); c) support crossings and double slips.
- ✅ ~~**(Q3) "Grid representation" of #29.**~~ **Decided 2026-11-04:** no grid representation for the OSM import:
  a) graph only, also in #31. Not taken: b) a grid cell per vertex (C2.2, dropped); c) a `GridTransitionMap`/`RailEnv`
  from the graph, which would need a graph-to-grid conversion flatland-rl does not have.
- ✅ ~~**(Q4) Where the dependencies go.**~~ **Decided 2026-11-04:** a) `osmnx_graph_import/requirements.txt` (C3.3):
  the repo has no `pyproject.toml`/`requirements.txt` yet (AGENTS.md) and the import is the only part with its own
  dependencies. Not taken: b) a `pyproject.toml` for the repo; c) a flatland-book page only.
  The CI job comes back with it, running the offline tests only (decided 2026-11-04, see 95a1226, 1a637c8, 99d5641).
- ✅ ~~**(Q5) The notebook's GGG implementations 1-3.**~~ **Decided 2026-11-04:** a) drop them and their `xfail` tests
  (C3.1). `build_double_vertex_graph` supersedes them, and the env and the stepper already run on it; on a reversing
  loop they would stop "Run all" before the stepper. Their history stays in git (c4bf7e4). Not taken: b) fix them.
- ✅ ~~**(Q6) Does `GraphRailEnv.from_graph` keep node and edge attributes?**~~ **Decided 2026-11-04:** check it first
  in C2.1, on branch `526-edge-lengths`. If it doesn't, `coordinates.py` reads them from the double vertex graph passed
  to `create_env` instead, keyed by vertex. Checked in the plan's revision on 2026-11-04: it keeps them - the notebook's
  step-through already reads `x`, `y` and `geometry` from `step_env.rail.g` (`train_location`, `edge_locations`,
  `create_map`). C2.1 reads `env.rail.g` and asserts it in its tests; the fallback is not needed.

## Findings

PR review comments, TODOs added in the PR and the PR's "Remaining" table, as of 0295bd3 (`main` 2e20db2). No code
review has been run yet (`/custom-code-review`).

- PR review comments (1-11) were added on 2026-11-04 from the threads of 2026-09-21 to 2026-10-21. Their line numbers
  refer to the commit the comment was made on: 1-2 to e9dc255, 3-9 to 1ea82f2, 10-11 to 0373c59.
- TODOs added in the PR (12-15) were added on 2026-11-04, line numbers at c2bc7b4. Each also is a row of the PR's
  "Remaining" table.
- Items of the PR's "Remaining" table not covered by a TODO (16-23) were added on 2026-11-04, anchored at the nearest
  line at c2bc7b4.
- Fixed: ✅ fixed, ⏭️ open and taken over by a row of the follow-ups table (its Findings column), — dropped, empty
  open (including planned as a step).
- "resolved" in Source marks threads resolved on GitHub; ❌ next to ✅ marks a finding fixed in the code whose PR comment
  thread is not resolved on GitHub yet.

| Fixed | ID | Source | Category | Severity | Finding | Commit message |
|---|---|---|---|---|---|---|
| ✅ | 1 | [PR comment](https://github.com/flatland-association/flatland-scenarios/pull/36#discussion_r4060285468), resolved | repo-size | medium | `osmnx_graph_import/flatland_osmnx_import_pipeline.ipynb:1`: the notebook is 35 MB with outputs - commit only the source? Fixed in 99d5641: outputs stripped (37 MB -> 90 KB), rule in AGENTS.md "Git". | `chore: do not run flatland_osmnx_import_pipeline.ipynb in ci and strip its outputs.` |
| ✅ | 3 | [PR comment](https://github.com/flatland-association/flatland-scenarios/pull/36#discussion_r4083020317), resolved | dependencies | medium | `osmnx_graph_import/flatland_osmnx_import_pipeline.ipynb:415`: update to flatland-rl `main` (5.0.0 preparation). Fixed in ec657ce. | `refactor: update deps from flatland_osmnx_import_pipeline.ipynb to flatland main (pre 5.0.0).` |
| ✅ | 5 | [PR comment](https://github.com/flatland-association/flatland-scenarios/pull/36#discussion_r4083035197), resolved | dependencies | medium | `osmnx_graph_import/flatland_osmnx_import_pipeline.ipynb:287`: same as finding 3 for the second dependency cell. Fixed in ec657ce, 781178b. | `chore: list osmnx_graph_import notebook dependencies inline and use flatland-rl branch 526-edge-lengths.` |
| ✅ | 6 | [PR comment](https://github.com/flatland-association/flatland-scenarios/pull/36#discussion_r4083043095), resolved | design | medium | `osmnx_graph_import/flatland_osmnx_import_pipeline.ipynb:307`: clean up the action handling (do it in flatland-rl). Fixed in 6dfdd4f: actions partitioned per vertex, checked with `_assert_actions_partitioned()`. | `feat: partition rail env actions in GGG and derive left/right switches from geometry.` |
| ✅ | 7 | [PR comment](https://github.com/flatland-association/flatland-scenarios/pull/36#discussion_r4083046158), resolved | design | medium | `osmnx_graph_import/flatland_osmnx_import_pipeline.ipynb:310`: as finding 6, second place. Fixed in 6dfdd4f. | `feat: partition rail env actions in GGG and derive left/right switches from geometry.` |
| ✅ | 8 | [PR comment](https://github.com/flatland-association/flatland-scenarios/pull/36#discussion_r4083062040), resolved | correctness | high | `osmnx_graph_import/flatland_osmnx_import_pipeline.ipynb:245`: what is needed to derive a digraph with only traversable transitions (no wrong-way moves through a switch)? Fixed in c4bf7e4, 0b9ff80: the double vertex graph. | `feat: build the double vertex graph (Montigel) from the track graph with a side-based construction.` |
| ✅ | 9 | [PR comment](https://github.com/flatland-association/flatland-scenarios/pull/36#discussion_r4083065544), resolved | correctness | medium | `osmnx_graph_import/flatland_osmnx_import_pipeline.ipynb:271`: verify what is lost when converting the MultiDiGraph to a DiGraph. Fixed in 489db5a, 28cb743: no parallel edges asserted, checks 1-2 of `load_track_graph`. | `feat: load_rail_graph loads and verifies the preprocessed rail graph from GraphML as DiGraph, use it in osmnx_graph_import notebook.` |
| ✅ ❌ | 10 | [PR comment](https://github.com/flatland-association/flatland-scenarios/pull/36#discussion_r4326224033) | robustness | high | `osmnx_graph_import/flatland_osmnx_import_pipeline.ipynb:345` (444 at 0373c59): verify the pipeline on other topologies; fail verbosely on degree > 3 or doubtful leg detection. Fixed in 17ff603 (C1.1 ✅): a clear geometry wins over incomplete `service`/`ref` tags, contradictions are warned about; b4d2dc3 (C1.2 ✅): nodes of degree > 3 are named with their OSM tags and a link. Running it on Bologna moved to follow-up #30 (Q1). | `feat: name the OSM node type of nodes with degree > 3 in the track graph verification.` |
| ✅ | 13 | TODO, also PR Remaining | maintainability | low | `osmnx_graph_import/flatland_osmnx_import_pipeline.ipynb:992`, `:1240`, `:1289`, `:1465`, `:1521`, `osmnx_graph_import/test_track_graph.py:98`, `:114`, `:124`, `AGENTS.md:60`: the notebook's GGG implementations 1-3 are wrong on reversing loops (and on a dead-end start), superseded by `build_double_vertex_graph`; `xfail` tests pin them. Fixed in 269ccca (C3.1 ✅): implementations 1-3, their verification and comparison sections, the two `xfail` tests and the AGENTS.md paragraph removed (Q5). | `refactor: drop the superseded GGG implementations from the notebook.` |
| ✅ | 14 | TODO, also PR Remaining | correctness | low | `osmnx_graph_import/flatland_osmnx_import_pipeline.ipynb:875`: the boundary paths do not come back round a reversing loop. Fixed in 269ccca (C3.1 ✅): the boundary paths are removed with implementation 1; the notebook checks edge duality only, the moves are checked in `test_track_graph.py`. | `refactor: drop the superseded GGG implementations from the notebook.` |
| ✅ | 15 | TODO, also PR Remaining | bug | low | `osmnx_graph_import/flatland_osmnx_import_pipeline.ipynb:891`: `rstrip("_prime")` strips characters, not the suffix; use `track_graph.opposite_vertex()`. Fixed in 269ccca (C3.1 ✅): `prime()` is removed; the remaining duality check uses `opposite_vertex()`. | `refactor: drop the superseded GGG implementations from the notebook.` |
| ✅ | 17 | PR Remaining | dependencies | medium | `osmnx_graph_import/flatland_osmnx_import_pipeline.ipynb:51`: no requirements file for the import; decide on flatland-book. Fixed in 1a0c73c (C3.3 ✅): `osmnx_graph_import/requirements.txt`, the notebook installs from it, and the CI job `run-osmnx-graph-import` runs the offline tests again; no flatland-book page (Q4). | `chore: add requirements for the osmnx graph import and run its tests in CI again.` |
| ✅ | 19 | PR Remaining | bug | low | `osmnx_graph_import/flatland_osmnx_import_pipeline.ipynb:766`: `explore_categorized(GGG)` shows every node gray - string vertex ids never match the integer switch ids. Fixed in 0295bd3 (C3.2 ✅): string vertices are mapped to their track node with `track_graph.track_node` first; on Walenstadt, GGG now shows 30 switch vertices. | `fix: color GGG nodes by switch category in explore_categorized.` |
| ✅ | 22 | PR Remaining | correctness | medium | `osmnx_graph_import/switch_geometry.py:108`: incomplete `service`/`ref` tags can mislead the through leg; let a clear geometry override that rule (way continuity still first). Fixed in 17ff603 (C1.1 ✅): a clear geometry now comes before the `service`/`ref` rule; tested on switch 1338901961, hard-coded from OSM. | `fix: let a clear switch geometry override the OSM service/ref rule.` |
|  | 12 | TODO, also PR Remaining | dependencies | medium | `osmnx_graph_import/double_vertex_graph_to_env.py:5`, `osmnx_graph_import/flatland_osmnx_import_pipeline.ipynb:51`, `:432`, `AGENTS.md:12`: depend on flatland-rl `main`, then a release, once branch `526-edge-lengths` (rl#542) is merged. Since 1a0c73c (C3.3 ✅), the notebook's two TODOs are replaced by one in `osmnx_graph_import/requirements.txt:2`. Open: planned in C3.4, blocked by rl#542. | `chore: depend on flatland-rl main for the osmnx graph import.` |
| ⏭️ | 16 | PR Remaining | feature | medium | `osmnx_graph_import/double_vertex_graph_to_env.py:112`: a hard-coded single-train timetable; generate a (multi-train) timetable. Open: taken over by follow-up #30 (follow-ups table). | `feat: generate a timetable for the osmnx graph rail env.` |
| ⏭️ | 18 | PR Remaining | feature | low | `osmnx_graph_import/double_vertex_graph_to_env.py:208`: no snapshot visualization; preferably an osmnx export with railway features. Open: taken over by the snapshot follow-up (follow-ups table). | `feat: export snapshots of the graph rail env with railway features.` |
| ⏭️ | 20 | PR Remaining | bug | medium | `osmnx_graph_import/flatland_osmnx_import_pipeline.ipynb:1807` (upstream, flatland-rl): reading graph trajectories back fails for every node id; read the position column as str and `literal_eval` only tuples, with a round-trip test. Open: taken over by a flatland-rl follow-up (follow-ups table). | `fix(trajectories): read graph node ids in trains_positions as strings.` |
| ⏭️ | 21 | PR Remaining | feature | low | `osmnx_graph_import/double_vertex_graph_to_env.py:208` (upstream, flatland-rl): `GraphRailEnv` cannot be saved, hence `no_save=True`. Open: taken over by a flatland-rl follow-up (follow-ups table). | `feat(graph): support persisting GraphRailEnv.` |
| ⏭️ | 23 | PR Remaining | robustness | medium | `osmnx_graph_import/double_vertex_graph_to_env.py:98` (upstream, flatland-rl): a train cannot end at a dead end, `GraphRailEnv.step()` fails an assertion for lack of a following entry point; `create_env` rejects such targets. Open: taken over by a flatland-rl follow-up (follow-ups table). | `fix(graph): allow targets without outgoing edge.` |
| — | 2 | [PR comment](https://github.com/flatland-association/flatland-scenarios/pull/36#discussion_r4060304568), resolved | planning | medium | `osmnx_graph_import/flatland_osmnx_import_pipeline.ipynb:1`: next steps - timetable, unit test with a policy reaching the target, snapshot visualization. Resolved on GitHub without a reply. The unit test is done in 4346c1a; timetable and snapshot are findings 16 and 18. | - |
| — | 4 | [PR comment](https://github.com/flatland-association/flatland-scenarios/pull/36#discussion_r4083033663), resolved | dependencies | medium | `osmnx_graph_import/flatland_osmnx_import_pipeline.ipynb:50`: full requirements.txt, run in CI, flatland-book? Resolved on GitHub without a code change. The requirements file and the CI job are finding 17 (C3.3). | - |
| — | 11 | [PR comment](https://github.com/flatland-association/flatland-scenarios/pull/36#discussion_r4335088806), resolved | design | low | `osmnx_graph_import/flatland_osmnx_import_pipeline.ipynb:214`: keep edge lengths as fractions (see rl#542 review)? Resolved on GitHub without a code change: kept as `Fraction`s, flatland rejects floats (decision of 2026-10-23). | - |

Issue references: the PR closes [#29](https://github.com/flatland-association/flatland-scenarios/issues/29); no code
or comment in `main..HEAD` references it. The PR description says "Closes #29".

## Decisions

| Date | Decision |
|---|---|
| 2026-10-20 | ✅ Notebooks are committed without outputs, and the notebook does not run in CI: live Overpass downloads failed with 502 (99d5641). |
| 2026-10-20 | ✅ flatland-rl from branch `526-edge-lengths` until rl#542 is merged (781178b); then `main` (C3.4). |
| 2026-10-23 | ✅ Edge lengths stay metres, as `Fraction`s, since flatland rejects floats (4346c1a). |
| 2026-10-23 | ✅ The double vertex graph is built by the local, side-based construction, which supports reversing loops (0b9ff80). |
| 2026-10-23 | ✅ A switch's through leg comes from OSM tags first, then geometry (53bee8d); C1.1 refines the order. |
| 2026-11-04 | ✅ Q1: the extent of the simplified Bologna is decided later, in follow-up #30; C1.3 moves there. |
| 2026-11-04 | ✅ Q2: nodes of degree > 3 (crossings, double slips) stay rejected, with a clear message (C1.2), and the extent is cut around them - in this PR and in #31. |
| 2026-11-04 | ✅ Q3: no grid representation for the OSM import, also in #31; C2.2 is dropped. |
| 2026-11-04 | ✅ Q4: the dependencies of the OSM import go into `osmnx_graph_import/requirements.txt` (C3.3); no flatland-book page. The CI job `run-osmnx-graph-import` comes back in C3.3, installing from it and running `pytest osmnx_graph_import` only; the notebook stays out of CI (99d5641). |
| 2026-11-04 | ✅ Q5: the notebook's GGG implementations 1-3 and their `xfail` tests are dropped (C3.1); the stepper runs on `build_double_vertex_graph`. |
| 2026-11-04 | ✅ Q6: C2.1 first checks that `GraphRailEnv.from_graph` keeps node and edge attributes; if not, the coordinates are read from the double vertex graph passed to `create_env`. It does keep them (the notebook's step-through reads them from `env.rail.g`), so C2.1 reads `env.rail.g`. |
