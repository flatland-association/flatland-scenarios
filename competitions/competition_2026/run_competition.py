import time

from scenario_generator.flatland_integration.run import main

if __name__ == '__main__':
    start_time = time.time()
    for scenario, sub_scenario, NUM in [
        ("level_0", "scenario_1_scene_1", 1)
    ]:
        main(
            num=NUM,
            start_seed=42,
            scenario=scenario,
            sub_scenario=sub_scenario,
            generate_movies=True,
            base_dir="competition_2026"
        )
    end_time = time.time()
    total = end_time - start_time
    print(f"Took {total :.2f}s overall.")
