import time

from scenario_generator.flatland_integration.run_dla import main

if __name__ == '__main__':
    start_time = time.time()
    for scenario, sub_scenario, NUM in [
        ("level_0", "level_0_scenario_1", 1)
    ]:
        main(
            num=NUM,
            start_seed=42,
            scenario=scenario,
            sub_scenario=sub_scenario,
            generate_movies=True
        )
    end_time = time.time()
    total = end_time - start_time
    print(f"Took {total :.2f}s overall.")
