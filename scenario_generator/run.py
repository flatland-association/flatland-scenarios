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
            use_alternative_at_first_intermediate_and_then_always_first_strategy=True,
            drop_next_threshold=20,
            seed=seed,
        )


def main(scenario: str, sub_scenario: str, generate_movies: bool = False, seed: int = None):
    data_dir = Path(f"./results/results_{sub_scenario}_{seed}_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
    data_dir.mkdir(exist_ok=False, parents=True)

    callbacks = None
    if generate_movies:
        callbacks = GenerateMovieCallbacks()

    PolicyRunner.create_from_policy(
        policy=DeadlockAvoidanceNoHeuristics(seed=seed),
        data_dir=data_dir,
        ep_id=sub_scenario,
        env=RailEnvPersister.load_new(f"./{scenario}/{sub_scenario}.pkl", obs_builder=FullEnvObservation())[0],
        callbacks=callbacks,
    )

    all_actions, all_trains_positions, all_trains_arrived, all_trains_rewards_dones_infos, env_stats, agent_stats = data_frame_for_trajectories(
        root_data_dir=Path(data_dir))
    print(f"normalized_reward={all_trains_arrived["normalized_reward"].sum()}")
    print(f"mean_normalized_reward={all_trains_arrived["normalized_reward"].mean()}")
    print(f"success_rate={all_trains_arrived["success_rate"].mean()}")


if __name__ == '__main__':
    NUM = 1
    START = 48
    for seed in range(START, START + NUM):
        main(
            "scenario_1",
            "scenario_1",
            seed=seed
            # generate_movies=True,
        )

# "scenario_1",
# "scenario_1",
#             count_num_opp_agents_towards_min_free_cell=False,
#             use_switches_heuristic=False,
#             use_entering_prevention=True,
#             use_alternative_at_first_intermediate_and_then_always_first_strategy=True,


# seed 42:
# normalized_reward=0.944669195111673
# mean_normalized_reward=0.944669195111673
# success_rate=1.0

# seed 43:
# normalized_reward=0.7407758580324952
# mean_normalized_reward=0.7407758580324952
# success_rate=0.7407407407407407

# seed 44:
# normalized_reward=0.8450063211125158
# mean_normalized_reward=0.8450063211125158
# success_rate=0.8703703703703703
