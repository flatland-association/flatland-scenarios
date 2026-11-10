import pytest

from flatland.core.effects_generator import EffectsGenerator
from flatland.envs.line_generators import sparse_line_generator
from flatland.envs.rail_env import RailEnv
from flatland.envs.rail_env_action import RailEnvActions
from flatland.envs.rail_generators import sparse_rail_generator
from flatland.envs.step_utils.states import TrainState
from scenario_generator.flatland_integration.malfunctions import ScheduledMalfunction, ScheduledMalfunctionEffectsGenerator


def _env(effects_generator) -> RailEnv:
    env = RailEnv(width=30, height=30, number_of_agents=2,
                  rail_generator=sparse_rail_generator(max_num_cities=2, seed=1),
                  line_generator=sparse_line_generator(seed=1),
                  effects_generator=effects_generator)
    env.reset(random_seed=1)
    for agent in env.agents:
        agent.earliest_departure = 0
    return env


def _run(env: RailEnv, num_steps: int):
    states = {}
    configurations = {}
    for _ in range(num_steps):
        env.step({h: RailEnvActions.MOVE_FORWARD for h in env.get_agent_handles()})
        states[env._elapsed_steps] = {a.handle: a.state for a in env.agents}
        configurations[env._elapsed_steps] = {a.handle: a.current_configuration for a in env.agents}
    return states, configurations


def test_scheduled_malfunction_breaks_exactly_during_window():
    step, duration = 5, 3
    env = _env(ScheduledMalfunctionEffectsGenerator([ScheduledMalfunction(handle=0, step=step, duration=duration)]))

    states, configurations = _run(env, 12)

    broken_steps = [s for s, by_handle in states.items() if by_handle[0] == TrainState.MALFUNCTION]
    assert broken_steps == list(range(step, step + duration))
    # agent 0 does not move during the malfunction
    assert len({configurations[s][0] for s in range(step - 1, step + duration)}) == 1
    # the other agent is unaffected
    assert all(by_handle[1] != TrainState.MALFUNCTION for by_handle in states.values())
    assert env.agents[0].malfunction_handler.num_malfunctions == 1


def test_scheduled_malfunction_before_departure_is_off_map():
    env = _env(ScheduledMalfunctionEffectsGenerator([ScheduledMalfunction(handle=0, step=1, duration=2)]))

    states, _ = _run(env, 4)

    assert [states[s][0] for s in (1, 2)] == [TrainState.MALFUNCTION_OFF_MAP] * 2
    assert states[3][0] != TrainState.MALFUNCTION_OFF_MAP


def test_scheduled_malfunction_skipped_with_warning_if_already_broken():
    env = _env(ScheduledMalfunctionEffectsGenerator([ScheduledMalfunction(handle=0, step=5, duration=3), ScheduledMalfunction(handle=0, step=6, duration=10)]))

    with pytest.warns(UserWarning, match="already in malfunction"):
        states, _ = _run(env, 12)

    assert [s for s, by_handle in states.items() if by_handle[0] == TrainState.MALFUNCTION] == [5, 6, 7]


def test_scheduled_malfunction_effects_generator_state_round_trip():
    malfunctions = [ScheduledMalfunction(handle=0, step=5, duration=3), ScheduledMalfunction(handle=1, step=7, duration=1)]
    eg = ScheduledMalfunctionEffectsGenerator(malfunctions)

    restored = EffectsGenerator.from_state(eg.__getstate__())

    assert isinstance(restored, ScheduledMalfunctionEffectsGenerator)
    assert restored.malfunctions == malfunctions
