from competitions.competition_2026.generate_competition_from_metadata_and_initial_scenario import get_scenes_from_timetable


def test_get_scenes_from_timetable():
    assert get_scenes_from_timetable({"name": "IC 1"}) == ["scene_1", "scene_4", "scene_5"]
    assert get_scenes_from_timetable({"name": "IC 2"}) == ["scene_2", "scene_5"]
    assert get_scenes_from_timetable({"name": "IC 3"}) == ["scene_3", "scene_4", "scene_5"]
    assert get_scenes_from_timetable({"name": "IC 4"}) == ["scene_4", "scene_5"]
    assert get_scenes_from_timetable({"name": "IC X"}) == ["scene_5"]
