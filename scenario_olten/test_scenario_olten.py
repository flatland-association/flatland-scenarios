import pickle
from pathlib import Path

import pytest
from flatland.evaluators.trajectory_evaluator import TrajectoryEvaluator
from flatland.integrations.interactiveai.interactiveai import FlatlandInteractiveAICallbacks
from flatland.trajectories.trajectories import Trajectory


@pytest.mark.parametrize(
    "scenario",
    ["olten", "olten_disrupted", "olten_partially_closed", ]
)
def test_olten(scenario: str):
    data_dir = Path(f"./scenario_olten/data/{scenario}")

    # scenario Olten has step every 3 seconds for an hour
    STEPS_ONE_HOUR = 1300
    # how many ms per step if replaying in real-time
    REALTIME_STEP_TO_MILLIS = 3600. / STEPS_ONE_HOUR * 1000.
    # run faster...
    SPEEDUP = 100000000.

    with (data_dir / "position_to_latlon.pkl").resolve().open("rb") as file_in:
        position_to_latlon_olten = pickle.loads(file_in.read())

    trajectory = Trajectory.load_existing(data_dir=data_dir, ep_id=scenario)

    # see above for configuration options
    cb = FlatlandInteractiveAICallbacks(position_to_latlon_olten, collect_only=True, step_to_millis=REALTIME_STEP_TO_MILLIS / SPEEDUP)
    TrajectoryEvaluator(trajectory, cb).evaluate()
    print(cb.events)
    print(cb.contexts)
