"""Tests for the isometric pygame frontend.

The pure modules (projection, snapshot, widgets) are tested directly.
The thread bridge is tested by running the sim on a worker thread and
answering prompts from the test thread — no pygame display required, so
these run headless in CI.
"""

import threading
import time

import pytest

from combat_sim.battlefield import Battlefield
from combat_sim.party import Party, Engagement
from combat_sim.combat import CombatContext, run_round
from combat_sim.creatures import Character, Monster
from combat_sim.dice import Dice
from combat_sim.actions import AttackAction, PassAction, MoveAction
from combat_sim.ui.human_ai import HumanAI
from combat_sim.ui.registry import Registry
from combat_sim.ui.parties import build_party

from combat_sim.ui.iso import isogeometry as iso
from combat_sim.ui.iso.snapshot import snapshot_board, TokenView
from combat_sim.ui.iso.widgets import stack_buttons, button_at
from combat_sim.ui.iso.frontend import IsoFrontend


# ---------------------------------------------------------------------------
# isogeometry — pure projection
# ---------------------------------------------------------------------------

class TestProjection:
    @pytest.mark.parametrize("tile", [(0, 0), (1, 0), (0, 1), (5, 3),
                                      (12, 9), (29, 0), (7, 7)])
    def test_round_trip(self, tile):
        origin = (640.0, 60.0)
        sx, sy = iso.tile_to_screen(*tile, origin, 48, 24)
        assert iso.screen_to_tile(sx, sy, origin, 48, 24) == tile

    def test_diamond_has_four_corners_around_centre(self):
        origin = (100.0, 100.0)
        cx, cy = iso.tile_to_screen(3, 2, origin, 48, 24)
        pts = iso.diamond_points(3, 2, origin, 48, 24)
        assert len(pts) == 4
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        # centre lies inside the corner bounding box
        assert min(xs) < cx < max(xs)
        assert min(ys) < cy < max(ys)

    def test_board_origin_centres_horizontally(self):
        ox, oy = iso.board_origin(30, 10, 1000, 56, 48, 24)
        # tile (0,0) and the mirror extents stay within the area width
        left = iso.tile_to_screen(0, 9, (ox, oy), 48, 24)[0] - 24
        right = iso.tile_to_screen(29, 0, (ox, oy), 48, 24)[0] + 24
        assert 0 <= left
        assert right <= 1000
        assert abs(left - (1000 - right)) <= 2  # roughly centred


# ---------------------------------------------------------------------------
# widgets — layout + hit testing
# ---------------------------------------------------------------------------

class TestWidgets:
    def test_stack_and_hit(self):
        actions = [("Attack", AttackAction(target=None)),  # target unused here
                   ("Pass", PassAction())]
        btns = stack_buttons(actions, panel_x=1000, panel_top=50, panel_w=300)
        assert len(btns) == 2
        # second button sits below the first
        assert btns[1].rect[1] > btns[0].rect[1]
        # a point inside the first button resolves to it
        x, y, w, h = btns[0].rect
        hit = button_at(btns, (x + 5, y + 5))
        assert hit is btns[0]
        # a point far away resolves to nothing
        assert button_at(btns, (0, 0)) is None


# ---------------------------------------------------------------------------
# snapshot — freezing live state
# ---------------------------------------------------------------------------

def _two_creature_ctx():
    bf = Battlefield(width=10, height=10)
    hero = Character(name="Karl", wounds_max=8, ws=1, stamina_max=2)
    beast = Monster(name="Wolf", wounds_max=6, hd=2)
    bf.register(hero, (1, 1))
    bf.register(beast, (8, 8))
    pa = Party(name="A", members=[hero])
    pb = Party(name="B", members=[beast])
    eng = Engagement(pa, pb, battlefield=bf)
    ctx = CombatContext(dice=Dice(seed=1), engagement=eng)
    return ctx, hero, beast


class TestSnapshot:
    def test_tokens_reflect_state(self):
        ctx, hero, beast = _two_creature_ctx()
        board = snapshot_board(ctx, active=hero)
        assert board.width == 10 and board.height == 10
        by_name = {t.name: t for t in board.tokens}
        assert set(by_name) == {"Karl", "Wolf"}
        karl = by_name["Karl"]
        assert (karl.x, karl.y) == (1, 1)
        assert karl.side == "A" and not karl.is_monster
        assert karl.is_active
        assert karl.stamina_max == 2
        wolf = by_name["Wolf"]
        assert wolf.side == "B" and wolf.is_monster
        assert not wolf.is_active

    def test_deregistered_creatures_are_omitted(self):
        ctx, hero, beast = _two_creature_ctx()
        ctx.engagement.battlefield.deregister(beast)
        board = snapshot_board(ctx)
        assert {t.name for t in board.tokens} == {"Karl"}


# ---------------------------------------------------------------------------
# thread bridge — prompts block until an action is submitted
# ---------------------------------------------------------------------------

class TestBridge:
    def test_prompt_action_round_trip(self):
        ctx, hero, beast = _two_creature_ctx()
        fe = IsoFrontend(speed=0.0)
        chosen = PassAction()
        options = [AttackAction(target=beast), chosen]
        box = {}

        def worker():
            box["result"] = fe.prompt_action(hero, options, ctx)

        t = threading.Thread(target=worker)
        t.start()
        # The request should appear; then we answer it.
        req = _wait_for(lambda: fe.pending_request())
        assert req.actor_name == "Karl" and req.kind == "action"
        assert beast.position in req.attack_targets
        fe.submit_action(chosen)
        t.join(timeout=2.0)
        assert not t.is_alive()
        assert box["result"] is chosen
        # request cleared after answering
        assert fe.pending_request() is None

    def test_abort_unblocks_with_keyboardinterrupt(self):
        ctx, hero, beast = _two_creature_ctx()
        fe = IsoFrontend(speed=0.0)
        box = {}

        def worker():
            try:
                fe.prompt_action(hero, [PassAction()], ctx)
            except KeyboardInterrupt:
                box["aborted"] = True

        t = threading.Thread(target=worker)
        t.start()
        _wait_for(lambda: fe.pending_request())
        fe.abort()
        t.join(timeout=2.0)
        assert box.get("aborted") is True

    def test_full_fight_through_run_round(self):
        """Drive a real round loop with a human-controlled creature whose
        decisions come through the IsoFrontend bridge. The test thread
        auto-answers (attack if offered, else pass) until someone wins or
        the round cap is hit."""
        reg = Registry()
        map_def = reg.maps()[0]
        bf = Battlefield(width=map_def.width, height=map_def.height,
                         blocked=set(map_def.blocked))
        dice = Dice(seed=3)
        pa = build_party(reg.templates(side="A")[0], map_def, bf, dice=dice)
        pb = build_party(reg.templates(side="B")[0], map_def, bf, dice=dice)

        fe = IsoFrontend(speed=0.0)
        for c in pa.members:
            c.ai = HumanAI(fe)

        eng = Engagement(pa, pb, battlefield=bf)
        ctx = CombatContext(dice=dice, engagement=eng,
                            on_action=fe.on_action_resolved)

        done = threading.Event()

        def loop():
            rounds = 0
            while (not pa.is_defeated and not pb.is_defeated
                   and rounds < 40):
                fe.on_round_start(ctx)
                run_round((pa, pb), ctx)
                rounds += 1
            done.set()

        t = threading.Thread(target=loop, daemon=True)
        t.start()

        answered = 0
        last_answered = None
        deadline = time.time() + 15.0
        while not done.is_set() and time.time() < deadline:
            req = fe.pending_request()
            # Dedupe by identity: between our submit and the worker
            # clearing it, the same request object is still visible, and
            # the next prompt (e.g. a counterattack offer) can replace it
            # too fast to ever observe a None gap.
            if req is None or req is last_answered:
                time.sleep(0.001)
                continue
            fe.submit_action(_pick(req))
            last_answered = req
            answered += 1

        if not done.is_set():
            fe.abort()
            pytest.fail("round loop did not finish within deadline")
        assert answered >= 1
        assert ctx.round_no > 0


# ---------------------------------------------------------------------------
# render — draws onto an off-screen Surface (no window / display needed)
# ---------------------------------------------------------------------------

class TestRender:
    def test_draw_frame_and_setup_do_not_raise(self):
        pygame = pytest.importorskip("pygame")
        try:
            pygame.font.init()
        except Exception:  # pragma: no cover - exotic builds
            pytest.skip("pygame font unavailable")

        from combat_sim.ui.iso import render
        from combat_sim.ui.iso.frontend import IsoFrontend

        ctx, hero, beast = _two_creature_ctx()
        fonts = {"small": pygame.font.SysFont(None, 22),
                 "big": pygame.font.SysFont(None, 30)}
        surf = pygame.Surface((1280, 760))

        # setup splash
        render.draw_setup(surf, fonts)

        # a full combat frame with a live decision request
        board = snapshot_board(ctx, active=hero)
        fe = IsoFrontend(speed=0.0)
        options = [AttackAction(target=beast), PassAction()]
        request = fe._build_action_request(hero, options, ctx)
        lo = render.compute_layout(board, 1280, 760)
        buttons = stack_buttons(list(request.buttons), panel_x=lo.panel_x,
                                panel_top=52, panel_w=lo.panel_w)
        render.draw_frame(surf, fonts, board, request, buttons, lo, (0, 0))

        # and the end-of-combat overlay path
        from combat_sim.combat import CombatResult
        result = CombatResult(rounds=3, winner="A", log=[])
        render.draw_frame(surf, fonts, board, None, [], lo, (0, 0),
                          result=result)


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _pick(req):
    for label, action in req.buttons:
        if isinstance(action, AttackAction):
            return action
    for label, action in req.buttons:
        if isinstance(action, PassAction):
            return action
    return req.buttons[0][1]


def _wait_for(predicate, timeout=2.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        val = predicate()
        if val:
            return val
        time.sleep(0.001)
    raise AssertionError("condition not met within timeout")
