from pathlib import Path

import pytest

from flatland.evaluators.trajectory_analysis import data_frame_for_trajectories
from flatland.trajectories.policy_runner import generate_trajectory_from_policy
from flatland_baselines.deadlock_avoidance_heuristic.policy.deadlock_avoidance_policy import DeadLockAvoidancePolicy


class DeadlockAvoidanceNoHeuristics(DeadLockAvoidancePolicy):
    def __init__(self):
        super().__init__(count_num_opp_agents_towards_min_free_cell=False, use_switches_heuristic=False)


def main(scenario: str, data_dir: str):
    Path(data_dir).mkdir(exist_ok=False)
    generate_trajectory_from_policy([
        "--data-dir", data_dir,
        "--ep-id", scenario,
        "--env-path", f"./{scenario}/{scenario}.pkl",
        "--policy-pkg", "scenario_generator.run", "--policy-cls", "DeadlockAvoidanceNoHeuristics",
        "--obs-builder-pkg", "flatland_baselines.deadlock_avoidance_heuristic.observation.full_env_observation", "--obs-builder-cls", "FullEnvObservation",
        "--callbacks-pkg", "flatland.callbacks.generate_movie_callbacks", "--callbacks-cls", "GenerateMovieCallbacks"
    ])


if __name__ == '__main__':
    data_dir = "./results20260126_1911"  #
    with pytest.raises(SystemExit) as e_info:
        main("scenario_1", data_dir)
        assert e_info.value.code == 0

    all_actions, all_trains_positions, all_trains_arrived, all_trains_rewards_dones_infos, env_stats, agent_stats = data_frame_for_trajectories(
        root_data_dir=Path(data_dir))
    print(f"normalized_reward={all_trains_arrived["normalized_reward"].sum()}")
    print(f"mean_normalized_reward={all_trains_arrived["normalized_reward"].mean()}")
    print(f"success_rate={all_trains_arrived["success_rate"].mean()}")
