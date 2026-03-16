import cProfile
import time

from scenario_generator.flatland_integration.run import run_with_policy

from flatland_baselines.deadlock_avoidance_heuristic.policy.TimingCallbacks import TimingCallbacks
from flatland_baselines.deadlock_avoidance_heuristic.policy.deadlock_avoidance_debug_callbacks import DeadlockAvoidanceDebugCallbacks
from flatland_baselines.deadlock_avoidance_heuristic.policy.deadlock_avoidance_policy import DeadLockAvoidancePolicy
from flatland_baselines.deadlock_avoidance_heuristic.observation.full_env_observation import FullEnvObservation


class DeadlockAvoidanceHeuristics(DeadLockAvoidancePolicy):
    def __init__(self,
                 use_alternative_at_first_intermediate_and_then_always_first_strategy=2,
                 seed: int = None,
                 audit: bool = False,
                 ):
        super().__init__(
            count_num_opp_agents_towards_min_free_cell=False,
            use_switches_heuristic=False,
            use_entering_prevention=True,
            use_alternative_at_first_intermediate_and_then_always_first_strategy=use_alternative_at_first_intermediate_and_then_always_first_strategy,
            drop_next_threshold=20,
            k_shortest_path_cutoff=450,
            seed=seed,
            audit=audit,
        )

def run_dla(scenario: str,
            sub_scenario: str,
            base_dir: str = None,
            generate_movies: bool = False,
            seed: int = None,
            use_alternative_at_first_intermediate_and_then_always_first_strategy: int = 2,
            audit: bool = False,
            ):
    
    policy = DeadlockAvoidanceHeuristics(
        seed=seed,
        use_alternative_at_first_intermediate_and_then_always_first_strategy=use_alternative_at_first_intermediate_and_then_always_first_strategy,
        audit=audit,
    )

    callbacks = [DeadlockAvoidanceDebugCallbacks(policy), TimingCallbacks()]
    obs_builder = FullEnvObservation()
    
    return run_with_policy(
        scenario=scenario,
        sub_scenario=sub_scenario,
        base_dir=base_dir,
        generate_movies=generate_movies,
        seed=seed,
        policy=policy,
        callbacks=callbacks,
        obs_builder=obs_builder,
    )

def main(num, start_seed, scenario, sub_scenario, base_dir=None, generate_movies=False):
    start_time = time.time()
    ress = []
    for seed in range(start_seed, start_seed + num):
        ress.append(run_dla(
            scenario,
            sub_scenario,
            base_dir=base_dir,
            seed=seed,
            generate_movies=generate_movies,
            audit=True,
        ))
    end_time = time.time()
    total = end_time - start_time
    print(f"Took {total :.2f}s for {num}")
    return ress


if __name__ == '__main__':
    profiling = False

    for scenario, sub_scenario, NUM in [
        ("scenario_1", "scenario_1_initial", 1),
        ("scenario_1", "scenario_1_generated", 1),
        ("scenario_2", "scenario_2_initial", 10),
        ("scenario_2", "scenario_2_generated", 10),
        ("scenario_3", "scenario_3_initial", 10),
        ("scenario_3", "scenario_3_generated", 10),
    ]:
        if profiling:
            cProfile.run(f'main(num={NUM},start_seed=48, scenario="{scenario}", sub_scenario="{sub_scenario}")', sort='cumtime', filename="run.hprof")
        else:
            main(num=NUM, start_seed=48, scenario=scenario, sub_scenario=sub_scenario)
