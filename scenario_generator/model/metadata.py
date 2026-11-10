from pathlib import Path
from typing import List, Any

from scenario_generator.model.config import to_malfunction_parameters
from scenario_generator.model.scenario import Scenario, ScenarioBuilder


def derive_scenario_from_initial_scenario_and_metadata(initial_scenario: Scenario, level_metadata, scenario_metadata, timetables=None) -> Scenario:
    # merge defaults with scenario-specific specs
    timetable_specs = _merge(level_metadata, scenario_metadata, "timetableSpecs")
    malfunction_specs = to_malfunction_parameters(_merge(level_metadata, scenario_metadata, "malfunctionSpecs"))
    departure_malfunction_specs = to_malfunction_parameters(_merge(level_metadata, scenario_metadata, "departureMalfunctionSpecs"))
    seed = scenario_metadata.get("seed", None)
    derived_scenario = (
        ScenarioBuilder(initial_scenario)
        # take timetables passed to override (all) timetables from initial scenario
        .add_timetables_from_specs(timetable_specs, timetables)
        .add_malfunction_from_specs(malfunction_specs)
        .add_departure_malfunction_from_specs(departure_malfunction_specs)
        .add_seed_from_specs(seed)
        .build()
    )
    return derived_scenario


def _merge(level_metadata, scenario_metadata, key) -> dict[Any, Any] | None:
    _defaults = level_metadata["defaults"].get(key, None)
    _specifics = scenario_metadata.get(key, None)
    if _defaults is not None and _specifics is not None:
        return {**_defaults, **_specifics}
    elif _defaults is not None:
        return _defaults
    elif _specifics is not None:
        return _specifics
    else:
        return None


def derive_scenarios_from_initial_scenario_and_metadata(initial_scenario: Scenario, metadata, output_folder: Path, create_pkl: bool) -> List[Scenario]:
    scenarios = []
    for level_metadata in metadata["levels"]:
        example_name = level_metadata["name"]

        for scenario_metadata in level_metadata["scenarios"]:
            scenario_name_ = scenario_metadata["name"]

            derived_scenario = derive_scenario_from_initial_scenario_and_metadata(initial_scenario, level_metadata, scenario_metadata)

            output_folder.mkdir(parents=True, exist_ok=True)
            derived_scenario.save(name=f'{example_name}_{scenario_name_}', folder=output_folder / example_name, create_pkl=create_pkl)
            scenarios.append(derived_scenario)
    return scenarios
