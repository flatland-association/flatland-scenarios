import time
from datetime import datetime
from pathlib import Path

from flatland.callbacks.generate_movie_callbacks import GenerateMovieCallbacks
from flatland.envs.persistence import RailEnvPersister
from flatland.evaluators.trajectory_analysis import data_frame_for_trajectories
from flatland.trajectories.policy_runner import PolicyRunner
from flatland_baselines.deadlock_avoidance_heuristic.observation.full_env_observation import FullEnvObservation
from flatland_baselines.deadlock_avoidance_heuristic.policy.deadlock_avoidance_policy import DeadLockAvoidancePolicy


class DeadlockAvoidanceNoHeuristics(DeadLockAvoidancePolicy):
    def __init__(self, seed: int = None):
        super().__init__(
            count_num_opp_agents_towards_min_free_cell=False,
            use_switches_heuristic=False,
            use_entering_prevention=True,
            use_alternative_at_first_intermediate_and_then_always_first_strategy=2,
            drop_next_threshold=20,
            k_shortest_path_cutoff=100,
            seed=seed,
        )


def run(scenario: str, sub_scenario: str, generate_movies: bool = False, seed: int = None):
    data_dir = Path(f"./results/results_{sub_scenario}_{seed}_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
    data_dir.mkdir(exist_ok=False, parents=True)

    callbacks = None
    if generate_movies:
        callbacks = GenerateMovieCallbacks()

    start_time = time.time()
    PolicyRunner.create_from_policy(
        policy=DeadlockAvoidanceNoHeuristics(seed=seed),
        data_dir=data_dir,
        ep_id=sub_scenario,
        env=RailEnvPersister.load_new(f"./{scenario}/{sub_scenario}.pkl", obs_builder=FullEnvObservation())[0],
        callbacks=callbacks,
    )
    end_time = time.time()
    print(f"Took {end_time - start_time:.2f}s")
    all_actions, all_trains_positions, all_trains_arrived, all_trains_rewards_dones_infos, env_stats, agent_stats = data_frame_for_trajectories(
        root_data_dir=Path(data_dir))
    print(f"normalized_reward={all_trains_arrived["normalized_reward"].sum()}")
    print(f"mean_normalized_reward={all_trains_arrived["normalized_reward"].mean()}")
    print(f"success_rate={all_trains_arrived["success_rate"].mean()}")


def main(num=10, start_seed=42):
    for seed in range(start_seed, start_seed + num):
        run(
            "scenario_1",
            "scenario_1",
            seed=seed
            # generate_movies=True,
        )


if __name__ == '__main__':
    # cProfile.run('main()', sort='cumtime', filename="run.hprof")
    NUM = 10
    start_time = time.time()
    main(num=NUM)
    end_time = time.time()
    total = end_time - start_time
    print(f"Took {total :.2f}s for {NUM}")
