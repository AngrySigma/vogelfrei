"""LiveTerminalFrontend — a single-screen variant of TerminalFrontend.

Same terminal play as the base frontend, but the combat view never
scrolls: it's drawn once into the alternate screen buffer and redrawn
*in place* each turn (the map updates, HP/stamina update, the action
menu sits at the bottom). Everything that the base frontend would have
spooled into scrollback — every round's board, every move snapshot,
plus a one-line event trail — is appended to a logfile instead, so the
full play-by-play is there to read afterward.

Only the per-turn prompts and render hooks are overridden; map/party
setup is inherited and runs in the normal terminal *before* the live
screen takes over (on the first ``on_round_start``).
"""

from __future__ import annotations
from typing import TYPE_CHECKING, Optional

from . import render
from . import prompts
from .frontend import TerminalFrontend
from .screen import LiveScreen, LogFile

if TYPE_CHECKING:
    from ...actions import Action
    from ...combat import CombatContext, CombatResult
    from ...creatures import Creature


class LiveTerminalFrontend(TerminalFrontend):
    """Single-screen terminal frontend. Use as a context manager so the
    alternate screen buffer is always restored, even on Ctrl-C::

        with LiveTerminalFrontend() as fe:
            run_game(fe, registry)
    """

    def __init__(self, log_path: str = "combat.log",
                 screen: Optional[LiveScreen] = None) -> None:
        self.screen = screen if screen is not None else LiveScreen()
        self.log = LogFile(log_path)

    # ------------------------------------------------------------------
    # Per-turn prompts
    # ------------------------------------------------------------------

    def prompt_action(self, actor: "Creature",
                      options: list["Action"],
                      ctx: "CombatContext") -> "Action":
        # Redraw the current state, then let the shared menu print itself
        # below the frame and read the player's choice. The next redraw
        # (the action resolving, or round start) wipes the menu away.
        self.screen.redraw(render.render_round(ctx))
        return prompts.prompt_action_menu(actor, options, ctx)

    def prompt_reaction(self, actor: "Creature",
                        attacker: "Creature",
                        ctx: "CombatContext") -> "Action":
        self.screen.redraw(render.render_round(ctx))
        return prompts.prompt_reaction_menu(actor, attacker, ctx)

    # ------------------------------------------------------------------
    # Render hooks
    # ------------------------------------------------------------------

    def on_round_start(self, ctx: "CombatContext") -> None:
        # First round start is where setup ends and live play begins.
        if not self.screen.active:
            self.screen.start()
        frame = render.render_round(ctx)
        self.screen.redraw(frame)
        self.log.write_block(frame)
        self.log.flush_log(ctx)

    def on_action_resolved(self, actor: "Creature", action: "Action",
                           ctx: "CombatContext") -> None:
        # Every action gets a one-line trail entry in the log.
        self.log.write(f"  - {render.event_line(actor, action)}")
        self.log.flush_log(ctx)
        # Mirror the base policy for the live board: only moves change
        # positions and need an immediate redraw so AI moves don't
        # teleport; wound changes from attacks surface in the status pane
        # at the next prompt / round start.
        from ...actions import MoveAction, MoveAndAttackAction
        if isinstance(action, (MoveAction, MoveAndAttackAction)):
            frame = render.render_round(ctx)
            self.screen.redraw(frame)
            self.log.write_block(frame)

    def on_combat_end(self, result: "CombatResult",
                      ctx: "CombatContext") -> None:
        # Drop back to the normal screen so the summary lands in real
        # scrollback (and survives the program exiting).
        self.screen.stop()
        self.log.flush_log(ctx)
        self._log_summary(result)
        super().on_combat_end(result, ctx)
        print(f"\nFull play-by-play log: {self.log.path}")

    # ------------------------------------------------------------------
    # Helpers / lifecycle
    # ------------------------------------------------------------------

    def _log_summary(self, result: "CombatResult") -> None:
        lines = [
            "============================",
            f" Combat over after {result.rounds} round(s)",
            f" Winner: {result.winner or 'draw (max rounds reached)'}",
            "============================",
        ]
        self.log.write_block("\n".join(lines))

    def __enter__(self) -> "LiveTerminalFrontend":
        return self

    def __exit__(self, *exc: object) -> bool:
        # Always restore the terminal and close the file, even on Ctrl-C.
        self.screen.stop()
        self.log.close()
        return False
