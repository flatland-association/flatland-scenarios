import json
import tempfile
from importlib import resources
from pathlib import Path

from scenario_generator.examples.generate_examples_from_metadata_and_initial_scenario import generate_examples_from_metadata_and_initial_scenario


def test_generate_examples_from_metadata_and_initial_scenario():
    with tempfile.TemporaryDirectory() as tmpdirname:
        tmpdir = Path(tmpdirname)

        examples_path = resources.files("scenario_generator.examples")

        with resources.as_file(examples_path.joinpath("example_2/example_2_initial.json")) as initial_scenario_file_name, \
                resources.as_file(examples_path.joinpath("metadata_example_scenarios_test.json")) as metadata_file_name:
            generate_examples_from_metadata_and_initial_scenario(
                initial_scenario_file_name=str(initial_scenario_file_name),
                metadata_file_name=str(metadata_file_name),
                create_pkl=True,
                output_folder=tmpdir
            )

        files = {str(f.relative_to(tmpdirname)) for f in tmpdir.rglob("**/*") if f.is_file()}
        assert files == {"example_2/example_2_test.pkl", "example_2/example_2_test.json"}

        with (tmpdir / "example_2/example_2_test.json").open() as f:
            data = json.load(f)
            print(data)

            assert data['flatlandLine'] == {
                'agent_positions': [[[[9, 30]], [[25, 39], [26, 39], [27, 39], [28, 39]], [[46, 64]]],
                                    [[[47, 64]], [[28, 39], [27, 39], [26, 39], [25, 39]], [[9, 29]]],
                                    [[[26, 10]], [[25, 39], [26, 39], [27, 39], [28, 39]], [[26, 71]]],
                                    [[[27, 71]], [[28, 39], [27, 39], [26, 39], [25, 39]], [[27, 10]]]],
                'agent_directions': [[[2], [1, 1, 1, 1]], [[3], [3, 3, 3, 3]], [[1], [1, 1, 1, 1]], [[3], [3, 3, 3, 3]]],
                'agent_targets': [[46, 64], [9, 29], [26, 71], [27, 10]],
                'agent_speeds': [1, 1, 1, 1]
            }
            assert data['flatlandTimetable'] == {
                'earliest_departures': [[0, 28, None], [0, 47, None], [0, 31, None], [0, 34, None]],
                'latest_arrivals': [[None, 26, 73], [None, 45, 75], [None, 29, 63], [None, 32, 63]],
                'max_episode_steps': 150
            }


def test_generate_examples_from_metadata_and_initial_scenario_empty_filter():
    with tempfile.TemporaryDirectory() as tmpdirname:
        tmpdir = Path(tmpdirname)

        examples_path = resources.files("scenario_generator.examples")

        with resources.as_file(examples_path.joinpath("example_2/example_2_initial.json")) as initial_scenario_file_name, \
                resources.as_file(examples_path.joinpath("metadata_example_scenarios_test_empty_filter.json")) as metadata_file_name:
            generate_examples_from_metadata_and_initial_scenario(
                initial_scenario_file_name=str(initial_scenario_file_name),
                metadata_file_name=str(metadata_file_name),
                create_pkl=True,
                output_folder=tmpdir
            )

        files = {str(f.relative_to(tmpdirname)) for f in tmpdir.rglob("**/*") if f.is_file()}
        assert files == {"example_2/example_2_test.pkl", "example_2/example_2_test.json"}

        with (tmpdir / "example_2/example_2_test.json").open() as f:
            data = json.load(f)
            print(data)

            assert data['flatlandLine'] == {
                'agent_positions': [],
                'agent_directions': [],
                'agent_targets': [],
                'agent_speeds': []
            }
            assert data['flatlandTimetable'] == {
                'earliest_departures': [],
                'latest_arrivals': [],
                'max_episode_steps': 0
            }


def test_generate_examples_from_metadata_and_initial_scenario_post_sample():
    with tempfile.TemporaryDirectory() as tmpdirname:
        tmpdir = Path(tmpdirname)

        examples_path = resources.files("scenario_generator.examples")

        with resources.as_file(examples_path.joinpath("example_2/example_2_initial.json")) as initial_scenario_file_name, \
                resources.as_file(examples_path.joinpath("metadata_example_scenarios_test_post_sampler.json")) as metadata_file_name:
            generate_examples_from_metadata_and_initial_scenario(
                initial_scenario_file_name=str(initial_scenario_file_name),
                metadata_file_name=str(metadata_file_name),
                create_pkl=True,
                output_folder=tmpdir
            )

        files = {str(f.relative_to(tmpdirname)) for f in tmpdir.rglob("**/*") if f.is_file()}
        assert files == {"example_2/example_2_test.pkl", "example_2/example_2_test.json"}

        with (tmpdir / "example_2/example_2_test.json").open() as f:
            data = json.load(f)
            print(data)

            assert len(data['flatlandLine']['agent_positions']) == 3
            assert len(data['flatlandLine']['agent_directions']) == 3
            assert len(data['flatlandLine']['agent_targets']) == 3
            assert len(data['flatlandLine']['agent_speeds']) == 3
            assert len(data['flatlandTimetable']['earliest_departures']) == 3
            assert len(data['flatlandTimetable']['latest_arrivals']) == 3

            for d in data['flatlandLine']['agent_positions']:
                assert d in [[[[9, 30]], [[25, 39], [26, 39], [27, 39], [28, 39]], [[46, 64]]],
                             [[[47, 64]], [[28, 39], [27, 39], [26, 39], [25, 39]], [[9, 29]]],
                             [[[26, 10]], [[25, 39], [26, 39], [27, 39], [28, 39]], [[26, 71]]],
                             [[[27, 71]], [[28, 39], [27, 39], [26, 39], [25, 39]], [[27, 10]]]]
            for d in data['flatlandLine']['agent_directions']:
                assert d in [[[2], [1, 1, 1, 1]], [[3], [3, 3, 3, 3]], [[1], [1, 1, 1, 1]], [[3], [3, 3, 3, 3]]]
            for d in data['flatlandLine']['agent_targets']:
                assert d in [[46, 64], [9, 29], [26, 71], [27, 10]]
            for d in data['flatlandLine']['agent_speeds']:
                assert d in [1, 1, 1, 1]

            for d in data['flatlandTimetable']['earliest_departures']:
                assert d in [[0, 28, None], [0, 47, None], [0, 31, None], [0, 34, None]]
            for d in data['flatlandTimetable']['latest_arrivals']:
                assert d in [[None, 26, 73], [None, 45, 75], [None, 29, 63], [None, 32, 63]]
