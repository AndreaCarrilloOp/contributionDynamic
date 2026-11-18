from dataclasses import replace
from datetime import date
from xml.etree import ElementTree

from contribution_dynamic.calendar import Day, demo_calendar
from contribution_dynamic.scenarios.chess import (
    FIRST_MOVE,
    LEFT,
    PAWN_SCALES,
    STAGING_ROW,
    STEP,
    TOP,
    board_weeks,
    legal_move,
    plan_match,
    queen_rays,
    render_chess,
)

NS = {"s": "http://www.w3.org/2000/svg"}


def test_chess_geometry():
    cases = {
        "pawn": ((1, 1), (0, 1)),
        "knight": ((2, 1), (2, 2)),
        "bishop": ((3, 3), (3, 2)),
        "rook": ((0, 4), (1, 3)),
        "queen": ((3, 0), (2, 3)),
        "king": ((1, 1), (0, 2)),
    }
    for piece, (yes, no) in cases.items():
        assert legal_move(piece, (0, 0), yes)
        assert not legal_move(piece, (0, 0), no)
        assert not legal_move(piece, (0, 0), (0, 0))
    assert legal_move("pawn", (3, 3), (4, 2), -1)


def test_queen_cannot_jump_over_standing_pawn():
    visible = set(queen_rays((2, 2), {(2, 4), (4, 4)}, 53))
    assert (2, 4) in visible and (2, 5) not in visible
    assert (4, 4) in visible and (5, 5) not in visible


def test_one_continuous_legal_route_captures_all_pawns():
    demo = demo_calendar()
    for days in (demo, tuple(replace(d, count=1) for d in demo)):
        match = plan_match(days)
        assert match is not None
        assert match == plan_match(days)
        pending = {(d.week, d.weekday): d for d in days if d.count}
        current = match.home
        assert current[1] == STAGING_ROW
        last = 0.0
        for move in match.moves:
            assert move.origin == current
            assert last < move.start < move.arrive < match.restore
            assert move.destination in set(queen_rays(current, set(pending), board_weeks(days)))
            assert legal_move("queen", move.origin, move.destination)
            assert move.day == pending.pop(move.destination, None)
            current, last = move.destination, move.arrive
        assert not pending
        assert current == match.home
        assert last < match.restore < match.cycle


def test_sparse_calendar_starts_immediately():
    day = Day(date(2026, 11, 17), 9, 2, 52, 4)
    match = plan_match((day,))
    assert match is not None
    move = match.moves[0]
    assert move.start == FIRST_MOVE and move.day == day
    assert move.arrive < 1


def test_svg_preserves_coordinates_and_exact_api_level():
    day = Day(date(2026, 11, 17), 99, 2, 52, 1)
    for theme in ("dark", "light"):
        root = ElementTree.fromstring(render_chess((day,), theme))
        cell = root.find(".//s:g[@id='calendar']/s:rect", NS)
        assert cell is not None
        assert cell.attrib["fill"] == "#f0d9b5"
        assert cell.attrib["data-level"] == "1"
        pawn = root.find(".//s:g[@data-piece='pawn']", NS)
        assert pawn is not None
        assert float(pawn.attrib["data-scale"]) == PAWN_SCALES[0]
        assert pawn.attrib["data-level"] == "1"
        assert int(cell.attrib["x"]) == LEFT + day.week * STEP
        assert int(cell.attrib["y"]) == TOP + day.weekday * STEP


def test_svg_single_queen_and_each_active_pawn_restores():
    days = demo_calendar()
    for theme in ("dark", "light"):
        svg = render_chess(days, theme)
        assert svg == render_chess(days, theme)
        root = ElementTree.fromstring(svg)
        assert len(root.findall(".//s:g[@data-piece='queen']", NS)) == 1
        pawns = root.findall(".//s:g[@data-piece='pawn']", NS)
        assert {p.attrib["data-pawn"] for p in pawns} == {
            d.date.isoformat() for d in days if d.count
        }
        assert len(root.findall(".//s:circle[@data-capture]", NS)) == len(pawns)
        for pawn in pawns:
            animation = pawn.find("s:animate[@attributeName='opacity']", NS)
            assert animation is not None
            assert animation.attrib["calcMode"] == "discrete"
            values = animation.attrib["values"].split(";")
            assert values[0] == values[-1] == "1"
            assert "0" in values
        for animation in root.findall(".//s:*[@keyTimes]", NS):
            keys = list(map(float, animation.attrib["keyTimes"].split(";")))
            assert keys[0] == 0 and keys[-1] == 1
            assert all(a < b for a, b in zip(keys, keys[1:]))
            assert len(keys) == len(animation.attrib["values"].split(";"))


def test_empty_calendar_has_no_pieces_or_animations():
    for days in ((), (Day(date(2026, 11, 17), 0, 2, 52),)):
        root = ElementTree.fromstring(render_chess(days))
        assert not root.findall(".//s:g[@data-piece]", NS)
        assert not root.findall(".//s:animate", NS)


def test_checkerboard_and_pawn_size_encode_separate_information():
    days = (
        Day(date(2026, 11, 15), 0, 0, 52),
        Day(date(2026, 11, 16), 7, 1, 52, 4),
        Day(date(2026, 11, 17), 1, 2, 52, 1),
        Day(date(2026, 11, 18), 8, 3, 52, 2),
        Day(date(2026, 11, 19), 3, 4, 52, 3),
    )
    for theme in ("dark", "light"):
        root = ElementTree.fromstring(render_chess(days, theme))
        cells = root.findall(".//s:g[@id='calendar']/s:rect", NS)
        assert [c.attrib["fill"] for c in cells] == [
            "#f0d9b5", "#b58863", "#f0d9b5", "#b58863", "#f0d9b5"
        ]
        pawns = root.findall(".//s:g[@data-piece='pawn']", NS)
        assert len(pawns) == 4
        for pawn in pawns:
            level = int(pawn.attrib["data-level"])
            assert float(pawn.attrib["data-scale"]) == PAWN_SCALES[level-1]
