from pathlib import Path

from flatland.evaluators.trajectory_analysis import data_frame_for_trajectories
from flatland.trajectories.policy_runner import generate_trajectory_from_policy


def main(scenario: str, data_dir: str):
    Path(data_dir).mkdir(exist_ok=True)
    generate_trajectory_from_policy([
        "--data-dir", data_dir,
        "--ep-id", scenario,
        "--env-path", f"./{scenario}/{scenario}.pkl",
        "--policy-pkg", "flatland_baselines.deadlock_avoidance_heuristic.policy.deadlock_avoidance_policy", "--policy-cls", "DeadLockAvoidancePolicy",
        "--obs-builder-pkg", "flatland_baselines.deadlock_avoidance_heuristic.observation.full_env_observation", "--obs-builder-cls", "FullEnvObservation",
        "--callbacks-pkg", "flatland.callbacks.generate_movie_callbacks", "--callbacks-cls", "GenerateMovieCallbacks"
    ])


if __name__ == '__main__':
    data_dir = "./results20260126_1341"
    main("scenario_1", data_dir)
    all_actions, all_trains_positions, all_trains_arrived, all_trains_rewards_dones_infos, env_stats, agent_stats = data_frame_for_trajectories(root_data_dir=Path(data_dir))
    print(all_trains_arrived)
    print(all_trains_arrived["normalized_reward"].sum())
    print(all_trains_arrived["normalized_reward"].mean())
    print(all_trains_arrived["success_rate"].mean())