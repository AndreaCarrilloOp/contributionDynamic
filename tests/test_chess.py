from dataclasses import replace
from datetime import date
from xml.etree import ElementTree

import pytest

from contribution_dynamic.calendar import Day, demo_calendar, month_label_positions
from contribution_dynamic.scenarios.chess import (
    CELL,
    FIRST_MOVE,
    FOCUS,
    LEFT,
    PIECE_BY_LEVEL,
    STEP,
    TEAM,
    TOP,
    board_weeks,
    destinations,
    legal_move,
    plan_match,
    render_chess,
)

NS = {"s": "http://www.w3.org/2000/svg"}


def test_chess_geometry_and_blocking():
    assert legal_move("queen", (0, 0), (3, 3))
    assert legal_move("rook", (0, 0), (3, 0))
    assert legal_move("bishop", (0, 0), (2, 2))
    assert legal_move("knight", (0, 0), (2, 1))
    assert not legal_move("bishop", (0, 0), (2, 1))
    assert not legal_move("rook", (0, 0), (2, 2))
    visible = set(destinations("queen", (2, 2), {(2, 4)}, {(4, 4)}, 53))
    assert (2, 4) in visible and (2, 5) not in visible
    assert (3, 3) in visible and (4, 4) not in visible
    assert (5, 5) not in visible
    assert (4, 3) in set(destinations("knight", (2, 2), {(3, 2)}, {(3, 3)}, 53))


@pytest.mark.parametrize("dense", [False, True])
def test_team_route_covers_every_day_without_friendly_collisions(dense):
    days = demo_calendar()
    if dense:
        days = tuple(replace(d, count=1) for d in days)
    match = plan_match(days)
    assert match is not None
    assert match == plan_match(days)
    assert tuple(piece for piece, _ in match.homes) == TEAM
    positions = dict(match.homes)
    pending = {(d.week, d.weekday): d for d in days if d.count}
    last = 0.0
    used = set()
    for move in match.moves:
        assert move.origin == positions[move.piece]
        assert last < move.start < move.arrive < match.restore
        allies = {pos for piece, pos in positions.items() if piece != move.piece}
        assert legal_move(move.piece, move.origin, move.destination)
        assert move.destination in set(destinations(
            move.piece, move.origin, set(pending), allies, board_weeks(days),
        ))
        assert move.day == pending.pop(move.destination, None)
        if move.day:
            used.add(move.piece)
        positions[move.piece] = move.destination
        last = move.arrive
    assert not pending
    assert positions == dict(match.homes)
    assert last < match.restore < match.cycle
    assert used == set(TEAM)


def test_sparse_calendar_starts_immediately():
    day = Day(date(2026, 11, 17), 9, 2, 52, 4)
    match = plan_match((day,))
    assert match is not None
    assert match.moves[0].start == FIRST_MOVE
    assert match.moves[0].day == day
    assert match.moves[0].arrive < 1


@pytest.mark.parametrize("theme", ["dark", "light"])
def test_svg_uses_contiguous_board_and_stationary_level_coded_defenders(theme):
    days = demo_calendar()
    svg = render_chess(days, theme)
    assert svg == render_chess(days, theme)
    root = ElementTree.fromstring(svg)
    assert {e.attrib["data-attacker"] for e in root.findall(".//s:g[@data-attacker]", NS)} == (
        set(TEAM)
    )
    cells = root.findall(".//s:g[@id='calendar']/s:rect", NS)
    assert len(cells) == len(days)
    for cell, day in zip(cells, days, strict=True):
        assert cell.attrib["data-date"] == day.date.isoformat()
        assert int(cell.attrib["x"]) == LEFT + day.week*STEP
        assert int(cell.attrib["y"]) == TOP + day.weekday*STEP
        assert int(cell.attrib["width"]) == CELL == STEP
    pieces = root.findall(".//s:g[@data-piece='contribution']", NS)
    assert {p.attrib["data-piece-date"] for p in pieces} == {
        d.date.isoformat() for d in days if d.count
    }
    assert sum(p.attrib["opacity"] == "1" for p in pieces) == FOCUS
    match = plan_match(days)
    assert match is not None
    captures = [m for m in match.moves if m.day is not None]
    for i, (piece, move) in enumerate(zip(pieces, captures, strict=True)):
        assert piece.attrib["data-kind"] == PIECE_BY_LEVEL[int(piece.attrib["data-level"])]
        assert not piece.findall(".//s:animateTransform", NS)
        anim = piece.find("s:animate[@attributeName='opacity']", NS)
        assert anim is not None and anim.attrib["calcMode"] == "discrete"
        keys = [float(k)*match.cycle for k in anim.attrib["keyTimes"].split(";")]
        if i < FOCUS:
            assert keys[1] == pytest.approx(move.arrive, abs=1e-6)
        else:
            assert keys[1] == pytest.approx(captures[i-FOCUS].arrive+.02, abs=1e-6)
            assert keys[2] == pytest.approx(move.arrive, abs=1e-6)
    assert len(root.findall(".//s:circle[@data-reserve]", NS)) == len(pieces)-FOCUS


def test_header_and_empty_calendar():
    days = tuple(replace(d, count=0) for d in demo_calendar())
    for theme in ("dark", "light"):
        root = ElementTree.fromstring(render_chess(days, theme))
        assert not root.findall(".//s:g[@data-attacker]", NS)
        assert not root.findall(".//s:animate", NS)
        header = root.find(".//s:g[@id='month-labels']", NS)
        assert header is not None
        labels = [(int(e.attrib["x"]), e.text) for e in header.findall("s:text", NS)]
        assert labels == list(month_label_positions(days, LEFT, STEP, int(root.attrib["width"])))
        assert "Dec" in {label for _, label in labels}
