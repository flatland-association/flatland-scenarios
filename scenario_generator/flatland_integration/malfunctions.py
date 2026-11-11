"""
Scheduled malfunctions, under flatland-rl's own class path.

TODO remove the copy once the flatland-rl release in use ships `ScheduledMalfunctionEffectsGenerator`
(flatland-rl PR `feat/scheduled-malfunction-effects-generator`); import it from
`flatland.envs.malfunction_effects_generators` instead.

A `.pkl` stores its effects generator as a class path, which must be importable wherever the `.pkl` is loaded.
The copy is therefore registered as `flatland.envs.malfunction_effects_generators.ScheduledMalfunctionEffectsGenerator`
(only if flatland does not have it yet), so the `.pkl`s written now load unchanged once flatland ships the class.
flatland-ui-hub carries the same copy (`backend/app/utils/flatland_compat.py`).
"""
import warnings
from typing import List, NamedTuple, Union

from flatland.core.effects_generator import EffectsGenerator
from flatland.envs import malfunction_effects_generators as _mfg

if hasattr(_mfg, "ScheduledMalfunctionEffectsGenerator"):
    ScheduledMalfunction = _mfg.ScheduledMalfunction
    ScheduledMalfunctionEffectsGenerator = _mfg.ScheduledMalfunctionEffectsGenerator
else:
    class ScheduledMalfunction(NamedTuple):
        """
        A malfunction at a fixed step.

        The agent with `handle` is in malfunction during the steps `step, ..., step + duration - 1`,
        i.e. exactly `duration` steps.
        Steps are counted as `RailEnv._elapsed_steps` during `step()`, so the first call to `step()` is step 1.
        """
        handle: int
        step: int
        duration: int


    class ScheduledMalfunctionEffectsGenerator(EffectsGenerator["RailEnv"]):
        """
        Deterministic malfunctions: each `ScheduledMalfunction` breaks one given agent at a given step
        for a given number of steps.

        An agent still in malfunction when one of its scheduled malfunctions is due keeps its current malfunction;
        the scheduled one is skipped with a warning.
        """

        def __init__(self, malfunctions: List[Union[ScheduledMalfunction, List[int]]] = None):
            super().__init__()
            self._malfunctions = [ScheduledMalfunction(*m) for m in (malfunctions or [])]
            for m in self._malfunctions:
                if m.step < 1:
                    raise ValueError(f"{m}: step must be >= 1, the first call to step() is step 1.")
                if m.duration < 1:
                    raise ValueError(f"{m}: duration must be >= 1.")

        @property
        def malfunctions(self) -> List[ScheduledMalfunction]:
            return list(self._malfunctions)

        def on_episode_step_start(self, env: "RailEnv", *args, **kwargs) -> "RailEnv":
            for m in self._malfunctions:
                if m.step != env._elapsed_steps:
                    continue
                handler = env.agents[m.handle].malfunction_handler
                if handler.in_malfunction:
                    warnings.warn(f"Scheduled malfunction {m} skipped: agent {m.handle} already in malfunction "
                                  f"(malfunction_down_counter={handler.malfunction_down_counter}).")
                    continue
                handler.malfunction_down_counter = m.duration
            return env

        def __getstate__(self):
            return {
                "cls": self.fullname,
                "specs": {
                    "kwargs": {
                        "malfunctions": [list(m) for m in self._malfunctions],
                    }
                }
            }


    for _cls in (ScheduledMalfunction, ScheduledMalfunctionEffectsGenerator):
        _cls.__module__ = _mfg.__name__
        setattr(_mfg, _cls.__name__, _cls)
