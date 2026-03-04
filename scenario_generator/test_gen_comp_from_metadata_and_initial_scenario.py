import json
import tempfile
from pathlib import Path

from scenario_generator.gen_comp_from_metadata_and_initial_scenario import gen_comp_from_metadata_and_initial_scenario


def test_gen_comp_from_metadata_and_initial_scenario():
    with tempfile.TemporaryDirectory() as tmpdirname:
        tmpdir = Path(tmpdirname)
        gen_comp_from_metadata_and_initial_scenario(
            initial_scenario_file_name='scenario_generator/scene_sample_initial.json',
            metadata_file_name='scenario_generator/metadata_template.json',
            create_pkl=True,
            output_folder=tmpdir
        )
        files = {str(f.relative_to(tmpdirname)) for f in tmpdir.rglob("**/*") if f.is_file()}
        assert files == {"level_0/level_0_scenario_1.pkl", "level_0/level_0_scenario_1.json"}

        with (tmpdir / "level_0/level_0_scenario_1.json").open() as f:
            data = json.load(f)
            print(data)

            assert data['flatlandLine'] == {
                'agent_positions': [[[[51, 72]], [[38, 89], [38, 90], [38, 91], [38, 92]], [[14, 116], [14, 117], [14, 118], [14, 119]],
                                     [[2, 141], [3, 141], [4, 141], [5, 141]], [[3, 145]]]],
                'agent_directions': [[[1], [0, 0, 0, 0], [0, 0, 0, 0], [1, 1, 1, 1]]],
                'agent_targets': [[3, 145]],
                'agent_speeds': [1]
            }
            assert data['flatlandTimetable'] == {
                'earliest_departures': [[0, 37, 96, 136, None]],
                'latest_arrivals': [[None, 35, 94, 134, 142]],
                'max_episode_steps': 284
            }
