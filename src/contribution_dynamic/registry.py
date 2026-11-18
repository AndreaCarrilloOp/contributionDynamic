"""Scenario catalog shared by the CLI, action, and publishing pipeline."""

from contribution_dynamic.scenarios.blast import render_blast
from contribution_dynamic.scenarios.chess import render_chess
from contribution_dynamic.scenarios.invaders import render_invaders
from contribution_dynamic.scenarios.origami import render_origami
from contribution_dynamic.scenarios.tanks import render_tanks
from contribution_dynamic.svg import render

RENDERERS = {
    "motion": render,
    "tanks": render_tanks,
    "blast": render_blast,
    "chess": render_chess,
    "invaders": render_invaders,
    "origami": render_origami,
}
PUBLISHED_SCENARIOS = ("tanks", "blast", "chess", "invaders", "origami")
THEMES = ("dark", "light")
