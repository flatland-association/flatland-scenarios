def rail_generator_from_grid_map(grid_map, level_free_positions):
    def rail_generator(*args, **kwargs):
        return grid_map, {
            "agents_hints": {"city_positions": {}},
            "level_free_positions": level_free_positions,
        }

    return rail_generator


def line_generator_from_line(line):
    def line_generator(*args, **kwargs):
        return line

    return line_generator


def timetable_generator_from_timetable(timetable):
    def timetable_generator(*args, **kwargs):
        return timetable

    return timetable_generator
