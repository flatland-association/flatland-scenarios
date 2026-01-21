from pathlib import Path

from flatland.trajectories.policy_grid_runner import generate_trajectories_from_metadata

if __name__ == '__main__':
    metadata_csv = Path("./trajectories/malfunction_deadlock_avoidance_heuristics/metadata.csv").resolve()
    data_dir = Path("./trajectories/malfunction_deadlock_avoidance_heuristics").resolve()
    generate_trajectories_from_metadata([
        "--metadata-csv", metadata_csv,
        "--data-dir", data_dir,
        "--policy-pkg", "flatland_baselines.deadlock_avoidance_heuristic.policy.deadlock_avoidance_policy",
        "--policy-cls", "DeadLockAvoidancePolicy",
        "--obs-builder-pkg", "flatland_baselines.deadlock_avoidance_heuristic.observation.full_env_observation",
        "--obs-builder-cls", "FullEnvObservation"
    ])
