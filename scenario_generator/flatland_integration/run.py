import time
from datetime import datetime
from pathlib import Path

from flatland.callbacks.callbacks import make_multi_callbacks
from flatland.callbacks.generate_movie_callbacks import GenerateMovieCallbacks
from flatland.envs.persistence import RailEnvPersister
from flatland.envs.rewards import BaseDefaultRewards
from flatland.evaluators.trajectory_analysis import data_frame_for_trajectories
from flatland.trajectories.policy_runner import PolicyRunner


def run_with_policy(scenario: str,
                    sub_scenario: str,
                    base_dir: Path = None,
                    results_dir: Path = Path("results"),
                    generate_movies: bool = False,
                    seed: int = None,
                    policy = None,
                    callbacks = None,
                    obs_builder = None,
                    ):
    data_dir = results_dir / f"results_{sub_scenario}_{seed}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    data_dir.mkdir(exist_ok=False, parents=True)

    if generate_movies:
        callbacks.append(GenerateMovieCallbacks())
    callbacks = make_multi_callbacks(*callbacks)

    start_time = time.time()

    PolicyRunner.create_from_policy(
        policy=policy,
        data_dir=data_dir,
        ep_id=sub_scenario,
        env=RailEnvPersister.load_new(str((base_dir if base_dir is not None else Path(".")) / scenario / f"{sub_scenario}.pkl"), obs_builder=obs_builder,
                                      rewards=BaseDefaultRewards())[0],
        callbacks=callbacks,
    )
    end_time = time.time()
    print(f"Took {end_time - start_time:.2f}s")
    all_actions, all_trains_positions, all_trains_arrived, all_trains_rewards_dones_infos, env_stats, agent_stats = data_frame_for_trajectories(
        root_data_dir=Path(data_dir))
    print(f"normalized_reward={all_trains_arrived['normalized_reward'].sum()}")
    print(f"mean_normalized_reward={all_trains_arrived['normalized_reward'].mean()}")
    print(f"success_rate={all_trains_arrived['success_rate'].mean()}")
    return all_actions, all_trains_positions, all_trains_arrived, all_trains_rewards_dones_infos, env_stats, agent_stats
