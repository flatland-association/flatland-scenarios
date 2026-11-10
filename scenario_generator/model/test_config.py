import json
from importlib import resources
from pathlib import Path

import numpy as np
import pytest

from flatland.core.effects_generator import find_effects_generator
from flatland.envs.malfunction_effects_generators import IntermediateStopMalfunctionEffectsGenerator
from flatland.envs.persistence import RailEnvPersister
from flatland.envs.rail_env import RailEnv
from flatland.envs.step_utils.states import TrainState
from scenario_generator.flatland_integration.malfunctions import ScheduledMalfunction, ScheduledMalfunctionEffectsGenerator
from scenario_generator.model.config import build_scenario_from_config, generate_scenario_from_config
from scenario_generator.model.scenario import Scenario

BREAKDOWN = {"malfunction_interval": 540, "malfunction_duration_min": 20, "malfunction_duration_max": 50}
DEPARTURE = {"malfunction_interval": 5, "malfunction_duration_min": 2, "malfunction_duration_max": 5}


def _initial_scenario_file() -> Path:
    with resources.as_file(resources.files("scenario_generator.examples").joinpath("example_2/example_2_initial.json")) as f:
        return Path(f)


@pytest.fixture
def initial_scenario() -> Scenario:
    return Scenario.load(str(_initial_scenario_file()))


def test_without_timetable_specs_keeps_tool_timetables(initial_scenario):
    scenario = build_scenario_from_config(initial_scenario, {})

    assert scenario.timetables == initial_scenario.timetables
    assert scenario.lines == initial_scenario.lines
    assert scenario.flatland_line == initial_scenario.flatland_line
    assert scenario.flatland_timetable == initial_scenario.flatland_timetable
    assert scenario.malfunction_params is None
    assert scenario.departure_malfunction_params is None
    assert scenario.scheduled_malfunctions == []
    assert scenario.to_effects_generator() is None
    assert "malfunctions" not in scenario.data


def test_with_timetable_specs_derives_timetables(initial_scenario):
    config = {"timetableSpecs": {"trainCategories": {"IC": {"times": 2, "periodicity": 30}}}}

    scenario = build_scenario_from_config(initial_scenario, config)

    assert [t['name'] for t in scenario.timetables] == ['IC 1.1', 'IC 1.2', 'IC 2.1', 'IC 2.2', 'IC 3.1', 'IC 3.2', 'IC 4.1', 'IC 4.2']
    assert len(scenario.flatland_line['agent_positions']) == 8


def test_scheduled_malfunctions_resolved_by_train_and_handle(initial_scenario):
    config = {"malfunctions": {"scheduled": [{"train": "RE 2.1", "step": 42, "duration": 10}, {"handle": 3, "step": 7, "duration": 1}]}}

    scenario = build_scenario_from_config(initial_scenario, config)

    assert scenario.scheduled_malfunctions == [ScheduledMalfunction(handle=5, step=42, duration=10), ScheduledMalfunction(handle=3, step=7, duration=1)]


def test_scheduled_malfunction_train_resolved_against_derived_timetables(initial_scenario):
    config = {
        "timetableSpecs": {"trainCategories": {"IC": {"times": 2, "periodicity": 30}}},
        "malfunctions": {"scheduled": [{"train": "IC 2.2", "step": 42, "duration": 10}]},
    }

    scenario = build_scenario_from_config(initial_scenario, config)

    assert scenario.scheduled_malfunctions == [ScheduledMalfunction(handle=3, step=42, duration=10)]


@pytest.mark.parametrize("spec, message", [
    ({"train": "IC 9.9", "step": 1, "duration": 1}, "not found"),
    ({"handle": 10, "step": 1, "duration": 1}, "out of range"),
    ({"train": "IC 1.1", "handle": 0, "step": 1, "duration": 1}, "exactly one"),
    ({"step": 1, "duration": 1}, "exactly one"),
    ({"train": "IC 1.1", "step": 0, "duration": 1}, "step >= 1"),
    ({"train": "IC 1.1", "step": 1, "duration": 0}, "duration >= 1"),
])
def test_invalid_scheduled_malfunctions_raise(initial_scenario, spec, message):
    with pytest.raises(ValueError, match=message):
        build_scenario_from_config(initial_scenario, {"malfunctions": {"scheduled": [spec]}})


def test_ambiguous_train_name_raises(initial_scenario):
    initial_scenario.data['timetables'][1]['name'] = 'IC 1.1'

    with pytest.raises(ValueError, match="ambiguous"):
        build_scenario_from_config(initial_scenario, {"malfunctions": {"scheduled": [{"train": "IC 1.1", "step": 1, "duration": 1}]}})


def test_config_malfunctions_override_tool_export_per_key(initial_scenario):
    initial_scenario.data['malfunctions'] = {"breakdown": BREAKDOWN, "scheduled": [{"train": "IC 1.1", "step": 1, "duration": 1}]}
    config = {"malfunctions": {"departure": DEPARTURE, "scheduled": [{"train": "IC 2.1", "step": 2, "duration": 2}]}}

    scenario = build_scenario_from_config(initial_scenario, config)

    assert np.isclose(scenario.malfunction_params.malfunction_rate, 1 / 540)
    assert np.isclose(scenario.departure_malfunction_params.malfunction_rate, 1 / 5)
    assert scenario.scheduled_malfunctions == [ScheduledMalfunction(handle=1, step=2, duration=2)]
    assert scenario.data['malfunctions'] == {"breakdown": BREAKDOWN, "departure": DEPARTURE, "scheduled": [{"train": "IC 2.1", "step": 2, "duration": 2}]}


def test_effects_generator_combines_departure_and_scheduled(initial_scenario):
    config = {"malfunctions": {"departure": DEPARTURE, "scheduled": [{"train": "IC 1.1", "step": 3, "duration": 4}]}}

    scenario = build_scenario_from_config(initial_scenario, config)
    effects_generator = scenario.to_effects_generator()

    assert isinstance(find_effects_generator(effects_generator, IntermediateStopMalfunctionEffectsGenerator), IntermediateStopMalfunctionEffectsGenerator)
    assert find_effects_generator(effects_generator, ScheduledMalfunctionEffectsGenerator).malfunctions == [ScheduledMalfunction(handle=0, step=3, duration=4)]


def test_generate_scenario_from_config_writes_json_and_pkl(tmp_path):
    config = {"malfunctions": {"breakdown": BREAKDOWN, "scheduled": [{"train": "RE 1.1", "step": 3, "duration": 4}]}}
    config_file = tmp_path / "config.json"
    config_file.write_text(json.dumps(config))

    generate_scenario_from_config(str(_initial_scenario_file()), str(config_file), name="experiment", output_folder=tmp_path, create_pkl=True)

    data = json.loads((tmp_path / "experiment.json").read_text())
    assert data['malfunctions'] == config['malfunctions']

    env, _ = RailEnvPersister.load_new(str(tmp_path / "experiment.pkl"))
    env: RailEnv
    assert np.isclose(env.malfunction_process_data.malfunction_rate, 1 / 540)
    assert find_effects_generator(env.effects_generator, ScheduledMalfunctionEffectsGenerator).malfunctions == [
        ScheduledMalfunction(handle=4, step=3, duration=4)]

    broken_steps = []
    for _ in range(10):
        env.step({})
        if env.agents[4].state in (TrainState.MALFUNCTION, TrainState.MALFUNCTION_OFF_MAP):
            broken_steps.append(env._elapsed_steps)
    assert broken_steps == [3, 4, 5, 6]
