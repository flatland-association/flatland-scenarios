import time

from scenario_generator.flatland_integration.run_dla import run_scenario


if __name__ == '__main__':
    start_time = time.time()
    for scenario, sub_scenario, NUM in [
        # ("example_1", "example_1_scenario", 1),
        ("example_2", "example_2_scenario", 1),
        # ("example_3", "example_3_scenario", 1)
    ]:
        run_scenario(
            num=NUM,
            start_seed=42,
            scenario=scenario,
            sub_scenario=sub_scenario,
            generate_movies=True
        )
    end_time = time.time()
    total = end_time - start_time
    print(f"Took {total :.2f}s overall.")
