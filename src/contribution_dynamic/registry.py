"""Scenario catalog shared by the CLI, action, and publishing pipeline."""

from contribution_dynamic.scenarios.abyss import render_abyss
from contribution_dynamic.scenarios.chess import render_chess
from contribution_dynamic.scenarios.factory import render_factory
from contribution_dynamic.scenarios.origami import render_origami
from contribution_dynamic.svg import render

RENDERERS = {
    "motion": render,
    "factory": render_factory,
    "origami": render_origami,
    "abyss": render_abyss,
    "chess": render_chess,
}
PUBLISHED_SCENARIOS = ("factory", "origami", "abyss", "chess")
THEMES = ("dark", "light")
