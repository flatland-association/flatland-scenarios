import json
import tempfile
from importlib import resources
from pathlib import Path

from competitions.competition_2026.generate_competition_from_metadata_and_initial_scenario import get_scenes_from_timetable, \
    generate_competition_from_metadata_and_initial_scenario
from flatland.envs.persistence import RailEnvPersister


def test_get_scenes_from_timetable():
    assert get_scenes_from_timetable({"name": "IC 1"}) == ["scene_1", "scene_4", "scene_5"]
    assert get_scenes_from_timetable({"name": "IC 2"}) == ["scene_2", "scene_5"]
    assert get_scenes_from_timetable({"name": "IC 3"}) == ["scene_3", "scene_4", "scene_5"]
    assert get_scenes_from_timetable({"name": "IC 4"}) == ["scene_4", "scene_5"]
    assert get_scenes_from_timetable({"name": "IC X"}) == ["scene_5"]


def test_generate_competition_from_metadata_and_initial_scenario():
    with tempfile.TemporaryDirectory() as tmpdirname:
        tmpdir = Path(tmpdirname)

        examples_path = resources.files("competitions.competition_2026")

        with resources.as_file(examples_path.joinpath("scene_sample_initial.json")) as initial_scenario_file_name, \
                resources.as_file(examples_path.joinpath("metadata_competition_sample.json")) as metadata_file_name, \
                resources.as_file(examples_path.joinpath("level_0", "level_0_scenario_1.json")) as expected_file_name:
            generate_competition_from_metadata_and_initial_scenario(
                initial_scenario_file_name=str(initial_scenario_file_name),
                metadata_file_name=str(metadata_file_name),
                levels=['level_0'],
                scenarios=['scenario_1'],
                create_pkl=True,
                output_folder=tmpdir,
            )
            print(list(tmpdir.rglob("**/*")))

            actual = json.load(open(tmpdir.joinpath("level_0", "level_0_scenario_1.json"), "r"))
            # dirty workaround: ignore due to changing IDs
            del actual["timetables"]
            expected = json.load(open(expected_file_name))
            # dirty workaround: ignore due to changing IDs
            del expected["timetables"]
            assert actual == expected

            env, _ = RailEnvPersister.load_new(f"{tmpdir}/level_0/level_0_scenario_1.pkl")
            assert len(env.effects_generator.__getstate__()) == 2


def test_generate_competition_from_metadata_and_initial_scenario_filter_levels():
    with tempfile.TemporaryDirectory() as tmpdirname:
        tmpdir = Path(tmpdirname)

        examples_path = resources.files("competitions.competition_2026")

        with resources.as_file(examples_path.joinpath("scene_sample_initial.json")) as initial_scenario_file_name, \
                resources.as_file(examples_path.joinpath("metadata_competition_sample.json")) as metadata_file_name, \
                resources.as_file(examples_path.joinpath("level_0", "level_0_scenario_1.json")) as expected_file_name:
            generate_competition_from_metadata_and_initial_scenario(
                initial_scenario_file_name=str(initial_scenario_file_name),
                metadata_file_name=str(metadata_file_name),
                levels=['level_XX'],
                scenarios=['scenario_1'],
                create_pkl=True,
                output_folder=tmpdir,
            )
            print(list(tmpdir.rglob("**/*")))
            assert len(list(tmpdir.rglob("**/*"))) == 0


def test_generate_competition_from_metadata_and_initial_scenario_filter_scenarios():
    with tempfile.TemporaryDirectory() as tmpdirname:
        tmpdir = Path(tmpdirname)

        examples_path = resources.files("competitions.competition_2026")

        with resources.as_file(examples_path.joinpath("scene_sample_initial.json")) as initial_scenario_file_name, \
                resources.as_file(examples_path.joinpath("metadata_competition_sample.json")) as metadata_file_name, \
                resources.as_file(examples_path.joinpath("level_0", "level_0_scenario_1.json")) as expected_file_name:
            generate_competition_from_metadata_and_initial_scenario(
                initial_scenario_file_name=str(initial_scenario_file_name),
                metadata_file_name=str(metadata_file_name),
                levels=['level_1'],
                scenarios=['scenario_XX'],
                create_pkl=True,
                output_folder=tmpdir,
            )
            print(list(tmpdir.rglob("**/*")))
            assert len(list(tmpdir.rglob("**/*"))) == 0
