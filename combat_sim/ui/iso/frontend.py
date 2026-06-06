"""IsoFrontend — the Frontend implementation behind the pygame view.

This object lives at the seam between two threads:

  * The **worker thread** runs ``run_game`` and calls the per-turn /
    render-hook methods here. Decisions (``prompt_action`` /
    ``prompt_reaction``) publish a :class:`DecisionRequest` and then
    *block* on a queue until the render thread answers.
  * The **main thread** (``IsoApp``) reads ``snapshot`` /
    ``pending_request`` each frame, draws them, and calls
    ``submit_action`` when the player clicks.

Setup (map / party / human / conditions) is inherited unchanged from
``TerminalFrontend`` and runs on the worker thread via ``input()``
before combat — exactly like the live terminal frontend deferred its
screen until the first round.

No pygame import here, so the bridge is unit-testable headless.
"""

from __future__ import annotations
import queue
import threading
import time
from typing import TYPE_CHECKING, Optional

from ..terminal import TerminalFrontend
from ..human_ai import HumanAI
from ...actions import (
    Action, AttackAction, MoveAction, MoveAndAttackAction,
    FullDefenceAction, PassAction, CounterAttackAction,
)
from ...movement import reachable_within
from .snapshot import BoardView, DecisionRequest, snapshot_board

if TYPE_CHECKING:
    from ...combat import CombatContext, CombatResult
    from ...creatures import Creature


# Sentinel placed on the action queue to abort a blocked prompt when the
# window is closed mid-decision, so the worker can unwind cleanly.
_ABORT = object()


class IsoFrontend(TerminalFrontend):
    """Frontend that renders combat in pygame and reads clicks back.

    Thread-safe surface for the render thread:
        ``phase``, ``snapshot()``, ``pending_request()``, ``result``,
        ``submit_action(action)``, ``abort()``.
    """

    def __init__(self, *, speed: float = 0.4) -> None:
        self.speed = speed                       # AI-turn pacing, seconds
        self._lock = threading.Lock()
        self._snapshot: Optional[BoardView] = None
        self._request: Optional[DecisionRequest] = None
        self._phase = "setup"                    # setup | combat | done
        self._result: "Optional[CombatResult]" = None
        self._answers: "queue.Queue[object]" = queue.Queue(maxsize=1)

    # ------------------------------------------------------------------
    # Render-thread surface (all lock-guarded)
    # ------------------------------------------------------------------

    @property
    def phase(self) -> str:
        with self._lock:
            return self._phase

    @property
    def result(self) -> "Optional[CombatResult]":
        with self._lock:
            return self._result

    def snapshot(self) -> Optional[BoardView]:
        with self._lock:
            return self._snapshot

    def pending_request(self) -> Optional[DecisionRequest]:
        with self._lock:
            return self._request

    def submit_action(self, action: Action) -> None:
        """Render thread → worker thread: deliver the player's choice."""
        try:
            self._answers.put_nowait(action)
        except queue.Full:
            pass  # a decision is already queued; ignore the extra click

    def abort(self) -> None:
        """Unblock any in-flight prompt so the worker can exit."""
        try:
            self._answers.put_nowait(_ABORT)
        except queue.Full:
            pass

    # ------------------------------------------------------------------
    # Internal publishing helpers (worker thread)
    # ------------------------------------------------------------------

    def _publish(self, *, snapshot: Optional[BoardView] = None,
                 request: Optional[DecisionRequest] = None,
                 phase: Optional[str] = None,
                 result: "Optional[CombatResult]" = None) -> None:
        with self._lock:
            if snapshot is not None:
                self._snapshot = snapshot
            self._request = request          # always set (None clears it)
            if phase is not None:
                self._phase = phase
            if result is not None:
                self._result = result

    def _await_answer(self) -> Action:
        """Block until the render thread submits an action (or abort)."""
        choice = self._answers.get()
        # Drop the just-shown request so the UI stops offering buttons.
        with self._lock:
            self._request = None
        if choice is _ABORT:
            raise KeyboardInterrupt("combat window closed")
        return choice  # type: ignore[return-value]

    # ------------------------------------------------------------------
    # Per-turn prompts (worker thread)
    # ------------------------------------------------------------------

    def prompt_action(self, actor: "Creature", options: list[Action],
                      ctx: "CombatContext") -> Action:
        request = self._build_action_request(actor, options, ctx)
        self._publish(snapshot=snapshot_board(ctx, active=actor),
                      request=request, phase="combat")
        return self._await_answer()

    def prompt_reaction(self, actor: "Creature", attacker: "Creature",
                        ctx: "CombatContext") -> Action:
        request = DecisionRequest(
            actor_name=actor.name,
            kind="reaction",
            buttons=(
                (f"Counterattack {attacker.name}", CounterAttackAction()),
                ("Pass", PassAction()),
            ),
        )
        self._publish(snapshot=snapshot_board(ctx, active=actor),
                      request=request, phase="combat")
        return self._await_answer()

    # ------------------------------------------------------------------
    # Render hooks (worker thread)
    # ------------------------------------------------------------------

    def on_round_start(self, ctx: "CombatContext") -> None:
        self._publish(snapshot=snapshot_board(ctx), request=None,
                      phase="combat")

    def on_action_resolved(self, actor: "Creature", action: Action,
                           ctx: "CombatContext") -> None:
        self._publish(snapshot=snapshot_board(ctx), request=None)
        # Pace AI turns so moves/attacks are watchable. The human's own
        # turn already took real time at the decision prompt.
        if not isinstance(actor.ai, HumanAI):
            time.sleep(self.speed)

    def on_combat_end(self, result: "CombatResult",
                      ctx: "CombatContext") -> None:
        self._publish(snapshot=snapshot_board(ctx), request=None,
                      phase="done", result=result)

    # ------------------------------------------------------------------
    # Decision-request construction
    # ------------------------------------------------------------------

    def _build_action_request(self, actor: "Creature",
                              options: list[Action],
                              ctx: "CombatContext") -> DecisionRequest:
        buttons: list[tuple[str, Action]] = []
        attack_targets: dict[tuple[int, int], Action] = {}

        for a in options:
            buttons.append((self._label(actor, a), a))
            # Let the player click an enemy token instead of the button.
            if isinstance(a, AttackAction) and a.target.position is not None:
                attack_targets.setdefault(a.target.position, a)

        # Free movement: any reachable square becomes a clickable
        # destination. This is the same set ``validate_move`` accepts,
        # so trusting it on the render thread needs no sim re-check.
        move_targets: dict[tuple[int, int], Action] = {}
        bf = ctx.engagement.battlefield
        if bf is not None and actor.position is not None:
            reach = reachable_within(actor.position, actor.movement_squares,
                                     bf, ignoring=actor)
            for tile in reach:
                if tile != actor.position:
                    move_targets[tile] = MoveAction(destination=tile)

        return DecisionRequest(
            actor_name=actor.name,
            kind="action",
            buttons=tuple(buttons),
            move_targets=move_targets,
            attack_targets=attack_targets,
        )

    @staticmethod
    def _label(actor: "Creature", action: Action) -> str:
        if isinstance(action, MoveAndAttackAction):
            return (f"Move {action.destination} → attack "
                    f"{action.attack.target.name}")
        if isinstance(action, AttackAction):
            wpn = action.weapon if action.weapon is not None else actor.weapon
            wname = wpn.name if wpn is not None else "unarmed"
            tag = " (ranged)" if (wpn is not None and wpn.is_ranged) else ""
            return f"Attack {action.target.name} w/ {wname}{tag}"
        if isinstance(action, MoveAction):
            return f"Move to {action.destination}"
        if isinstance(action, FullDefenceAction):
            return "Full Defence"
        if isinstance(action, CounterAttackAction):
            return "Counterattack"
        if isinstance(action, PassAction):
            return "Pass turn"
        return type(action).__name__
