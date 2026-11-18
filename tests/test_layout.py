from contribution_dynamic.layout import calendar_width


def test_width_has_no_trailing_cell_gap():
    assert calendar_width(47, 13, 10, 16, 53) == 749
    assert calendar_width(47, 13, 13, 16, 53) == 752
    assert calendar_width(47, 13, 10, 16, 54) == 762
