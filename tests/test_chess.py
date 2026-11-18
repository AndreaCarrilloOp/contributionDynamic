from dataclasses import replace
from datetime import date
from xml.etree import ElementTree

from contribution_dynamic.calendar import Day, demo_calendar, month_label_positions
from contribution_dynamic.scenarios.chess import (
    FIRST_MOVE,
    LEFT,
    PIECE_BY_LEVEL,
    PIECE_SCALES,
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


def test_queen_cannot_jump_over_standing_piece():
    visible = set(queen_rays((2, 2), {(2, 4), (4, 4)}, 53))
    assert (2, 4) in visible and (2, 5) not in visible
    assert (4, 4) in visible and (5, 5) not in visible


def test_one_continuous_legal_route_captures_all_pieces():
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
        assert cell.attrib["fill"] == "#f3e4bf"
        assert cell.attrib["data-level"] == "1"
        piece = root.find(".//s:g[@data-piece='contribution']", NS)
        assert piece is not None
        assert float(piece.attrib["data-scale"]) == PIECE_SCALES[1]
        assert piece.attrib["data-level"] == "1"
        assert piece.attrib["data-kind"] == "pawn"
        assert int(cell.attrib["x"]) == LEFT + day.week * STEP
        assert int(cell.attrib["y"]) == TOP + day.weekday * STEP


def test_svg_single_queen_and_each_active_piece_restores():
    days = demo_calendar()
    for theme in ("dark", "light"):
        svg = render_chess(days, theme)
        assert svg == render_chess(days, theme)
        root = ElementTree.fromstring(svg)
        assert len(root.findall(".//s:g[@data-piece='queen']", NS)) == 1
        pieces = root.findall(".//s:g[@data-piece='contribution']", NS)
        assert {p.attrib["data-piece-date"] for p in pieces} == {
            d.date.isoformat() for d in days if d.count
        }
        assert len(root.findall(".//s:circle[@data-capture]", NS)) == len(pieces)
        for piece in pieces:
            level = int(piece.attrib["data-level"])
            assert piece.attrib["data-kind"] == PIECE_BY_LEVEL[level]
            assert float(piece.attrib["data-scale"]) == PIECE_SCALES[level]
            animation = piece.find("s:animate[@attributeName='opacity']", NS)
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


def test_checkerboard_and_piece_type_encode_separate_information():
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
            "#f3e4bf", "#8f6c47", "#f3e4bf", "#8f6c47", "#f3e4bf"
        ]
        pieces = root.findall(".//s:g[@data-piece='contribution']", NS)
        assert len(pieces) == 4
        for piece in pieces:
            level = int(piece.attrib["data-level"])
            assert float(piece.attrib["data-scale"]) == PIECE_SCALES[level]


def test_distinct_piece_symbols_match_all_four_levels():
    days = tuple(Day(date(2026, 11, 15+level), 99, level, 52, level)
                 for level in range(1, 5))
    for theme in ("dark", "light"):
        root = ElementTree.fromstring(render_chess(days, theme))
        pieces = root.findall(".//s:g[@data-piece='contribution']", NS)
        assert {p.attrib["data-level"]: p.attrib["data-kind"] for p in pieces} == {
            "1": "pawn", "2": "knight", "3": "bishop", "4": "rook",
        }
        for piece in pieces:
            symbol = piece.find(".//s:use", NS)
            assert symbol is not None
            assert symbol.attrib["href"] == "#chess-" + piece.attrib["data-kind"]
            assert root.find(f".//s:g[@id='chess-{piece.attrib['data-kind']}']", NS) is not None


def test_stationary_pieces_disappear_on_arrival_and_restore_together():
    days = demo_calendar(42, 8)
    match = plan_match(days)
    assert match is not None
    captures = {m.day.date.isoformat(): m for m in match.moves if m.day is not None}
    for theme in ("dark", "light"):
        root = ElementTree.fromstring(render_chess(days, theme))
        pieces = root.findall(".//s:g[@data-piece='contribution']", NS)
        for piece in pieces:
            move = captures[piece.attrib["data-piece-date"]]
            x = LEFT + move.destination[0] * STEP + 5
            y = TOP + move.destination[1] * STEP + 5
            assert piece.attrib["transform"].startswith(f"translate({float(x)} {float(y)})")
            assert not piece.findall(".//s:animateTransform", NS)
            opacity = piece.find("s:animate[@attributeName='opacity']", NS)
            assert opacity is not None
            values = opacity.attrib["values"].split(";")
            keys = list(map(float, opacity.attrib["keyTimes"].split(";")))
            assert values[:3] == ["1", "0", "1"]
            assert abs(keys[1] * match.cycle - move.arrive) < 1e-6
            assert abs(keys[2] * match.cycle - match.restore) < 1e-6
            effect = root.find(f".//s:circle[@data-capture='{move.day.date.isoformat()}']", NS)
            assert effect is not None
            assert float(effect.attrib["cx"]) == x
            assert float(effect.attrib["cy"]) == y
        queen = root.find(".//s:g[@data-piece='queen']", NS)
        assert queen is not None
        movement = queen.find("s:animateTransform[@type='translate']", NS)
        assert movement is not None
        positions = movement.attrib["values"].split(";")
        assert positions[0] == positions[-1]
        assert len(set(positions)) > 1


def test_month_header_is_spaced_and_omits_weekdays():
    days = demo_calendar()
    for theme in ("dark", "light"):
        root = ElementTree.fromstring(render_chess(days, theme))
        header = root.find(".//s:g[@id='month-labels']", NS)
        assert header is not None
        assert header.attrib["font-family"] == "Georgia,serif"
        labels = header.findall("s:text", NS)
        expected = month_label_positions(days, LEFT, STEP, int(root.attrib["width"]))
        assert [(int(label.attrib["x"]), label.text) for label in labels] == list(expected)
        assert all(b[0] - a[0] >= 24 for a, b in zip(expected, expected[1:]))
        texts = {node.text for node in root.findall(".//s:text", NS)}
        assert not texts.intersection({"Mon", "Wed", "Fri"})
        assert "Dec" in texts
