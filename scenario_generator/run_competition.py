import time

from scenario_generator.run import main

if __name__ == '__main__':
    start_time = time.time()
    for scenario, sub_scenario, NUM in [
        ("level_0", "level_0_scene_1", 1),
        ("level_0", "level_0_scene_2", 1),
        ("level_0", "level_0_scene_3", 1),
        ("level_0", "level_0_scene_4", 1),
        ("level_0", "level_0_scene_5", 1),
    ]:
        main(
            num=NUM,
            start_seed=42,
            scenario=scenario,
            sub_scenario=sub_scenario,
            generate_movies=True,
            base_dir="competition"
        )
    end_time = time.time()
    total = end_time - start_time
    print(f"Took {total :.2f}s overall.")
