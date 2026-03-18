from importlib import resources

import numpy as np

from scenario_generator.model.scenario import Scenario, ScenarioBuilder


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


def test_scenario_to_timetable_generator_with_specs():
    examples_path = resources.files("scenario_generator.examples")

    with resources.as_file(examples_path.joinpath("example_2/example_2_initial.json")) as initial_scenario_file_name:
        initial_scenario = Scenario.load(str(initial_scenario_file_name))
    timetable_specs = {
        "IC": {
            "initialShift": 0,
            "periodicity": 30,
            "times": 20,
            "travelFactor": 1.05
        },
        "RE": {
            "initialShift": 0,
            "periodicity": 60,
            "times": 10,
            "travelFactor": 1.1
        }
    }
    timetable = initial_scenario.to_timetable_generator(timetable_specs)()

    derived_scenario = ScenarioBuilder(initial_scenario).add_timetables_from_specs(timetable_specs).build()
    assert derived_scenario.flatland_timetable != initial_scenario.flatland_timetable
    assert derived_scenario.flatland_timetable == timetable._asdict()
