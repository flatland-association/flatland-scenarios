from datetime import datetime
from pathlib import Path

import pytest

from flatland.evaluators.trajectory_analysis import data_frame_for_trajectories
from flatland.trajectories.policy_runner import generate_trajectory_from_policy
from flatland_baselines.deadlock_avoidance_heuristic.policy.deadlock_avoidance_policy import DeadLockAvoidancePolicy


class DeadlockAvoidanceNoHeuristics(DeadLockAvoidancePolicy):
    def __init__(self):
        super().__init__(
            count_num_opp_agents_towards_min_free_cell=False,
            use_switches_heuristic=False,
            use_entering_prevention=True,
            use_alternative_at_first_intermediate_and_then_always_first_strategy=True,
            seed=43,
        )


def main(scenario: str, sub_scenario: str, data_dir: str = None, generate_movies: bool = False):
    data_dir = f"./results_{sub_scenario}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"  #
    Path(data_dir).mkdir(exist_ok=False)
    with pytest.raises(SystemExit) as e_info:
        args = [
            "--data-dir", data_dir,
            "--ep-id", sub_scenario,
            "--env-path", f"./{scenario}/{sub_scenario}.pkl",
            "--policy-pkg", "scenario_generator.run", "--policy-cls", "DeadlockAvoidanceNoHeuristics",
            "--obs-builder-pkg", "flatland_baselines.deadlock_avoidance_heuristic.observation.full_env_observation", "--obs-builder-cls", "FullEnvObservation",

        ]
        if generate_movies:
            args += ["--callbacks-pkg", "flatland.callbacks.generate_movie_callbacks", "--callbacks-cls", "GenerateMovieCallbacks"]
        generate_trajectory_from_policy(args)
        assert e_info.value.code == 0

    all_actions, all_trains_positions, all_trains_arrived, all_trains_rewards_dones_infos, env_stats, agent_stats = data_frame_for_trajectories(
        root_data_dir=Path(data_dir))
    print(f"normalized_reward={all_trains_arrived["normalized_reward"].sum()}")
    print(f"mean_normalized_reward={all_trains_arrived["normalized_reward"].mean()}")
    print(f"success_rate={all_trains_arrived["success_rate"].mean()}")


if __name__ == '__main__':
    main(
        "scenario_1",
        "scenario_1",
        # generate_movies=True,
    )

# seed 42:
# normalized_reward=0.944669195111673
# mean_normalized_reward=0.944669195111673
# success_rate=1.0

# seed 43:
# normalized_reward=0.7407758580324952
# mean_normalized_reward=0.7407758580324952
# success_rate=0.7407407407407407
