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

    with (data_dir / "position_to_latlon.pkl").resolve().open("rb") as file_in:
        position_to_latlon_olten = pickle.loads(file_in.read())

    trajectory = Trajectory(data_dir=data_dir, ep_id=scenario)

    # see above for configuration options
    cb = FlatlandInteractiveAICallbacks(position_to_latlon_olten, collect_only=True, step_to_millis=0)
    TrajectoryEvaluator(trajectory, cb).evaluate()
    print(cb.events)
    print(cb.contexts)
