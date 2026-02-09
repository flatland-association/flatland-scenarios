import numpy as np

from scenario_generator.run import run

if __name__ == '__main__':
    for scenario, sub_scenario, seed, use_alternative_at_first_intermediate_and_then_always_first_strategy, expected_normalized_reward, expected_success_rate in [
        ("scenario_2", "scenario_2_initial", 48, 2, 0.973313, 1.0),
        ("scenario_2", "scenario_2_generated", 48, 2, 0.612999, 0.271429),
        # N.B. scenario_3 and scenario_3_generated has "Found loopy line" because with domain-logic always left in initial path finding, there is no path between the left-most tracks in the line (limitation of current DLA implementation or data problem, you decide...)
        ("scenario_3", "scenario_3_initial", 48, 2, 0.9322638146167558, 0.8571428571428571),
        # TODO disabling alternatives yields better results in scenario_3_generated, analyse in detail, e.g. does the penalty in the normalized reward come from skipping intermediate stops:
        ("scenario_3", "scenario_3_generated", 48, None, 0.810678, 0.913534),
        ("scenario_3", "scenario_3_generated", 48, 2, 0.6950677101473028, 0.3233082706766917),
        ("scenario_1", "scenario_1_initial", 48, 2, 0.958906, 1.0),
        # TODO analyse scenario_1_generated: what happens here?
        ("scenario_1", "scenario_1_generated", 48, 2, 0.818131696969697, 0.21),  # Took 798.57s
    ]:
        all_actions, all_trains_positions, all_trains_arrived, all_trains_rewards_dones_infos, env_stats, agent_stats = run(
            seed=seed, scenario=scenario,
            sub_scenario=sub_scenario,
            use_alternative_at_first_intermediate_and_then_always_first_strategy=use_alternative_at_first_intermediate_and_then_always_first_strategy,
            generate_movies=False,
            audit=True,
        )
        normalized_reward = all_trains_arrived["normalized_reward"].sum()
        mean_normalized_reward = all_trains_arrived["normalized_reward"].mean()
        success_rate = all_trains_arrived["success_rate"].mean()

        assert np.isclose(normalized_reward, expected_normalized_reward), (scenario, sub_scenario, normalized_reward, expected_normalized_reward)
        assert np.isclose(mean_normalized_reward, expected_normalized_reward), (scenario, sub_scenario, mean_normalized_reward, expected_normalized_reward)
        assert np.isclose(success_rate, expected_success_rate), (scenario, sub_scenario, success_rate, expected_success_rate)
