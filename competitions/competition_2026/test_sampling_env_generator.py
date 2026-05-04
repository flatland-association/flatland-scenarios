import numpy as np

from competitions.competition_2026.sampling_env_generator import sampling_env_generator
from flatland.envs.persistence import RailEnvPersister


def test_sampling_env_generator() -> None:
    sampling_env = sampling_env_generator(RailEnvPersister.load_new("level_0_scenario_1.pkl", load_from_package="competitions.competition_2026.level_0")[0])
    env, _ = RailEnvPersister.load_new("level_0_scenario_1.pkl", load_from_package="competitions.competition_2026.level_0")

    assert np.array_equal(env.rail.grid, sampling_env.rail.grid)
    assert env.agents == sampling_env.agents

    # verify sampling env produces new randomly sampled lines on the same grid
    sampling_env.reset()
    assert np.array_equal(env.rail.grid, sampling_env.rail.grid)
    assert len(env.agents) == len(sampling_env.agents)
    assert env.agents != sampling_env.agents

    # sanity check: reset on env loaded from file always produces same (see https://github.com/flatland-association/flatland-rl/pull/408)
    env_raw, _ = RailEnvPersister.load_new("level_0_scenario_1.pkl", load_from_package="competitions.competition_2026.level_0")
    env.reset()
    assert np.array_equal(env.rail.grid, env_raw.rail.grid)
    assert env.agents == env_raw.agents


def test_sampling_env_generator_line_length_3() -> None:
    sampling_env = sampling_env_generator(RailEnvPersister.load_new("level_0_scenario_1.pkl", load_from_package="competitions.competition_2026.level_0")[0], line_length=3)
    env, _ = RailEnvPersister.load_new("level_0_scenario_1.pkl", load_from_package="competitions.competition_2026.level_0")

    assert np.array_equal(env.rail.grid, sampling_env.rail.grid)
    assert env.agents == sampling_env.agents

    # verify sampling env produces new randomly sampled lines on the same grid
    sampling_env.reset()
    assert np.array_equal(env.rail.grid, sampling_env.rail.grid)
    assert len(env.agents) == len(sampling_env.agents)
    assert env.agents != sampling_env.agents

    # sanity check: reset on env loaded from file always produces same (see https://github.com/flatland-association/flatland-rl/pull/408)
    env_raw, _ = RailEnvPersister.load_new("level_0_scenario_1.pkl", load_from_package="competitions.competition_2026.level_0")
    env.reset()
    assert np.array_equal(env.rail.grid, env_raw.rail.grid)
    assert env.agents == env_raw.agents