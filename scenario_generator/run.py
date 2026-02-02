import cProfile
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
    def __init__(self,
                 use_alternative_at_first_intermediate_and_then_always_first_strategy=2,
                 seed: int = None,
                 ):
        super().__init__(
            count_num_opp_agents_towards_min_free_cell=False,
            use_switches_heuristic=False,
            use_entering_prevention=True,
            use_alternative_at_first_intermediate_and_then_always_first_strategy=use_alternative_at_first_intermediate_and_then_always_first_strategy,
            drop_next_threshold=20,
            k_shortest_path_cutoff=250,
            seed=seed,
            # verbose=False,
        )


def run(scenario: str, sub_scenario: str, generate_movies: bool = False, seed: int = None,
        use_alternative_at_first_intermediate_and_then_always_first_strategy: int = 2):
    data_dir = Path(f"./results/results_{sub_scenario}_{seed}_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
    data_dir.mkdir(exist_ok=False, parents=True)

    callbacks = None
    if generate_movies:
        callbacks = GenerateMovieCallbacks()

    start_time = time.time()
    PolicyRunner.create_from_policy(
        policy=DeadlockAvoidanceNoHeuristics(
            seed=seed,
            use_alternative_at_first_intermediate_and_then_always_first_strategy=use_alternative_at_first_intermediate_and_then_always_first_strategy
        ),
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
    return all_actions, all_trains_positions, all_trains_arrived, all_trains_rewards_dones_infos, env_stats, agent_stats


def main(num, start_seed, scenario, sub_scenario):
    for seed in range(start_seed, start_seed + num):
        run(
            scenario,
            sub_scenario,
            seed=seed,
            # generate_movies=True,
        )


if __name__ == '__main__':
    profiling = False
    NUM = 10
    start_time = time.time()
    for scenario, sub_scenario in [
        # ("scenario_2", "scenario_2"),
        # ("scenario_2", "scenario_2_generated"),
        ("scenario_3", "scenario_3"),
        # ("scenario_3", "scenario_3_generated"),
        # ("scenario_1", "scenario_1"),
        # ("scenario_1", "scenario_1_generated"),
    ]:
        if profiling:
            cProfile.run(f'main(num={NUM},start_seed=48, scenario="{scenario}", sub_scenario="{sub_scenario}")', sort='cumtime', filename="run.hprof")
        else:
            main(num=NUM, start_seed=48, scenario=scenario, sub_scenario=sub_scenario)
    end_time = time.time()
    total = end_time - start_time
    print(f"Took {total :.2f}s for {NUM}")
