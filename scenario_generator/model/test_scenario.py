from importlib import resources

import numpy as np

from flatland.envs.persistence import RailEnvPersister
from scenario_generator.flatland_integration.flatland_generators import stations_to_agents_hints, stations_to_stations_links
from scenario_generator.model.scenario import Scenario, ScenarioBuilder


def test_scenario_to_flatland_generators():
    examples_path = resources.files("scenario_generator.examples")
    with resources.as_file(examples_path.joinpath("example_2/example_2_initial.json")) as initial_scenario_file_name:
        scenario = Scenario.load(str(initial_scenario_file_name))

    rail, optionals = scenario.to_rail_generator()()
    assert np.array_equal(rail.grid, scenario.grid)
    assert optionals["level_free_positions"] == [tuple(v) for v in scenario.level_free_crossings]
    assert optionals["agents_hints"] == stations_to_agents_hints(scenario.stations)
    # every city has at least one platform, and city_positions/orientations/train_stations stay in lockstep
    assert len(optionals["agents_hints"]["city_positions"]) == len(scenario.stations)
    assert len(optionals["agents_hints"]["city_orientations"]) == len(scenario.stations)
    assert len(optionals["agents_hints"]["train_stations"]) == len(scenario.stations)
    assert optionals["stations_links"] == stations_to_stations_links(scenario.stations)

    line = scenario.to_line_generator()()
    assert scenario.flatland_line["agent_speeds"] == line.agent_speeds

    timetable = scenario.to_timetable_generator()()
    assert scenario.flatland_timetable == timetable._asdict()


def test_rail_env_exposes_and_persists_stations_links(tmp_path):
    examples_path = resources.files("scenario_generator.examples")
    with resources.as_file(examples_path.joinpath("example_2/example_2_initial.json")) as initial_scenario_file_name:
        scenario = Scenario.load(str(initial_scenario_file_name))

    env, _, _ = scenario.to_rail_env()
    assert env.stations_links == stations_to_stations_links(scenario.stations)
    assert len(env.stations_links.stations) == len(scenario.stations)

    RailEnvPersister.save(env, str(tmp_path / "env.pkl"))
    loaded_env, _ = RailEnvPersister.load_new(str(tmp_path / "env.pkl"))
    assert loaded_env.stations_links == env.stations_links


def test_scenario_to_timetable_generator_with_specs():
    examples_path = resources.files("scenario_generator.examples")

    with resources.as_file(examples_path.joinpath("example_2/example_2_initial.json")) as initial_scenario_file_name:
        initial_scenario = Scenario.load(str(initial_scenario_file_name))
    timetable_specs = {
        "trainCategories": {
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
    }
    timetable = initial_scenario.to_timetable_generator(timetable_specs)()

    derived_scenario = ScenarioBuilder(initial_scenario).add_timetables_from_specs(timetable_specs).build()
    assert derived_scenario.flatland_timetable != initial_scenario.flatland_timetable
    assert derived_scenario.flatland_timetable == timetable._asdict()
