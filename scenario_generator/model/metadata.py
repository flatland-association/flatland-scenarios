from flatland.envs.malfunction_generators import MalfunctionParameters
from scenario_generator.model.scenario import Scenario, ScenarioBuilder


def derive_scenario_from_initial_scenario_and_metadata(initial_scenario: Scenario, level_metadata, scenario_metadata, timetables=None) -> Scenario:
    # merge defaults with scenario-specific specs
    timetable_specs = {**level_metadata["defaults"]["timetableSpecs"], **scenario_metadata["timetableSpecs"]}

    malfunction_specs = scenario_metadata.get("malfunctionSpecs", None)
    if malfunction_specs is not None:
        malfunction_specs = MalfunctionParameters(
            min_duration=malfunction_specs["malfunction_duration_min"],
            max_duration=malfunction_specs["malfunction_duration_max"],
            malfunction_rate=1 / malfunction_specs["malfunction_interval"]
        )
    departure_malfunction_specs = scenario_metadata.get("departureMalfunctionSpecs", None)
    if departure_malfunction_specs is not None:
        departure_malfunction_specs = MalfunctionParameters(
            min_duration=departure_malfunction_specs["malfunction_duration_min"],
            max_duration=departure_malfunction_specs["malfunction_duration_max"],
            malfunction_rate=1 / departure_malfunction_specs["malfunction_interval"]
        )
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
