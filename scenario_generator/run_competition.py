import time

from scenario_generator.run import main

if __name__ == '__main__':
    start_time = time.time()
    for scenario, sub_scenario, NUM in [
        ("scene_1", "scene_1_initial", 1),
        ("scene_2", "scene_2_initial", 1),
        ("scene_3", "scene_3_initial", 1),
        ("scene_4", "scene_4_initial", 1),
        ("scene_5", "scene_5_initial", 1),
    ]:
        main(
            num=NUM,
            start_seed=42,
            scenario=scenario,
            sub_scenario=sub_scenario,
            generate_movies=True,
            base_dir="../flatland-rl/scenarios/OneDrive_1_23-02-2026"
        )
    end_time = time.time()
    total = end_time - start_time
    print(f"Took {total :.2f}s overall.")
