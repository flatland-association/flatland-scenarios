import warnings
from typing import List, NamedTuple

from flatland.core.effects_generator import EffectsGenerator


class ScheduledMalfunction(NamedTuple):
    handle: int
    step: int
    duration: int


class ScheduledMalfunctionEffectsGenerator(EffectsGenerator["RailEnv"]):
    """
    Deterministic malfunctions: agent `handle` is broken during steps [step, step + duration).

    Steps are counted like timetable times (`env._elapsed_steps` during the step, i.e. the first `env.step()` call is step 1).
    """

    def __init__(self, malfunctions: List[ScheduledMalfunction] = None):
        super().__init__()
        self._malfunctions = [ScheduledMalfunction(*m) for m in (malfunctions or [])]

    @property
    def malfunctions(self) -> List[ScheduledMalfunction]:
        return list(self._malfunctions)

    def on_episode_step_start(self, env: "RailEnv", *args, **kwargs) -> "RailEnv":
        for m in self._malfunctions:
            if m.step != env._elapsed_steps:
                continue
            handler = env.agents[m.handle].malfunction_handler
            if handler.in_malfunction:
                warnings.warn(f"Scheduled malfunction {m} skipped: agent {m.handle} is already in malfunction at step {m.step}.")
                continue
            # the counter is decremented once at the end of the step it is set in
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
