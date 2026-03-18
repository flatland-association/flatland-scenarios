from importlib import resources

import numpy as np

from scenario_generator.model.scenario import Scenario


def test_scenario_to_flatland_generators():
    examples_path = resources.files("scenario_generator.examples")
    with resources.as_file(examples_path.joinpath("example_2/example_2_initial.json")) as initial_scenario_file_name:
        scenario = Scenario.load(str(initial_scenario_file_name))

    rail, optionals = scenario.to_rail_generator()()
    print(optionals)
    assert np.array_equal(rail.grid, scenario.grid)
    assert optionals["level_free_positions"] == [tuple(v) for v in scenario.level_free_crossings]

    line = scenario.to_line_generator()()
    assert scenario.flatland_line["agent_speeds"] == line.agent_speeds

    timetable = scenario.to_timetable_generator()()
    assert scenario.flatland_timetable == timetable._asdict()
