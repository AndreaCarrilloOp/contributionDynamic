from datetime import date
from xml.etree import ElementTree

from contribution_dynamic.calendar import Day, demo_calendar
from contribution_dynamic.scenarios.chess import (
    CADENCE,
    FIRST_MOVE,
    LANES,
    LEFT,
    PIECES,
    RESTORE,
    STEP,
    TOP,
    board_weeks,
    legal_move,
    plan_captures,
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


def test_every_active_day_is_captured_once():
    days = demo_calendar()
    moves = plan_captures(days)
    assert len(moves) == len({move.day for move in moves})
    assert {move.day for move in moves} == {day for day in days if day.count}
    assert {move.piece for move in moves} == set(PIECES)
    assert moves == plan_captures(days)
    weeks = board_weeks(days)
    for move in moves:
        assert legal_move(move.piece, move.origin, move.destination, move.side)
        assert move.destination == (move.day.week, move.day.weekday)
        for x, y in (move.origin, move.destination):
            assert move.lane * weeks // LANES <= x < (move.lane + 1) * weeks // LANES
            assert 0 <= y < 7


def test_zones_are_independent_and_prioritize_intensity():
    moves = plan_captures(demo_calendar())
    for lane in range(LANES):
        sequence = [move for move in moves if move.lane == lane]
        assert sequence
        assert [m.start for m in sequence] == [
            FIRST_MOVE + i * CADENCE for i in range(len(sequence))
        ]
        assert all(a.day.count >= b.day.count for a, b in zip(sequence, sequence[1:]))
        assert all(a.start + RESTORE < b.start for a, b in zip(sequence, sequence[1:]))


def test_sparse_calendar_starts_immediately():
    day = Day(date(2026, 11, 17), 9, 2, 52, 4)
    move, = plan_captures((day,))
    assert move.start == FIRST_MOVE
    assert legal_move(move.piece, move.origin, move.destination, move.side)


def test_svg_preserves_coordinates_and_exact_api_level():
    day = Day(date(2026, 11, 17), 99, 2, 52, 1)
    for theme, color in (("dark", "#0e4429"), ("light", "#9be9a8")):
        root = ElementTree.fromstring(render_chess((day,), theme))
        cell = root.find(".//s:g[@id='calendar']/s:rect", NS)
        assert cell is not None
        assert cell.attrib["fill"] == color
        assert int(cell.attrib["x"]) == LEFT + day.week * STEP
        assert int(cell.attrib["y"]) == TOP + day.weekday * STEP


def test_svg_is_deterministic_and_has_valid_timelines():
    days = demo_calendar()
    for theme in ("dark", "light"):
        svg = render_chess(days, theme)
        assert svg == render_chess(days, theme)
        root = ElementTree.fromstring(svg)
        assert len(root.findall(".//s:g[@data-capture]", NS)) == sum(
            bool(day.count) for day in days
        )
        for tag in ("animate", "animateTransform"):
            for anim in root.findall(f".//s:{tag}[@keyTimes]", NS):
                keys = list(map(float, anim.attrib["keyTimes"].split(";")))
                assert keys[0] == 0 and keys[-1] == 1
                assert all(a < b for a, b in zip(keys, keys[1:]))
                assert len(keys) == len(anim.attrib["values"].split(";"))


def test_empty_calendar_has_no_captures():
    root = ElementTree.fromstring(render_chess(()))
    assert not root.findall(".//s:g[@data-capture]", NS)
    assert not root.findall(".//s:animate", NS)
