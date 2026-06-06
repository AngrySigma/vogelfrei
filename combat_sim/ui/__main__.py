"""CLI entry point: ``python -m combat_sim.ui``.

By default, walks the player through the full setup pipeline using the
terminal frontend. ``--scenario`` short-circuits map and party choice
by loading a preset battle configuration (a named map + named
templates) so you can jump straight into a familiar fight.
"""

from __future__ import annotations
import argparse
from contextlib import nullcontext
from dataclasses import dataclass

from .game import run_game
from .registry import Registry
from .terminal import TerminalFrontend, LiveTerminalFrontend


@dataclass
class Preset:
    """A named (map, party_a, party_b) bundle for quick launches."""
    key: str
    map_name: str
    party_a_key: str
    party_b_key: str
    description: str


PRESETS: dict[str, Preset] = {
    "duel": Preset(
        key="duel",
        map_name="Open Field",
        party_a_key="lone_warrior_a",
        party_b_key="lone_warrior_b",
        description="One-on-one chain+shield warrior duel on flat ground.",
    ),
    "pillar": Preset(
        key="pillar",
        map_name="Pillar Detour",
        party_a_key="lone_warrior_a",
        party_b_key="single_goblin_b",
        description="Lone warrior vs goblin, with a wall column between them.",
    ),
    "corridor": Preset(
        key="corridor",
        map_name="Corridor",
        party_a_key="two_warriors_a",
        party_b_key="goblin_mob_b",
        description="Two warriors hold a 1-square corridor against four goblins.",
    ),
    "archer": Preset(
        key="archer",
        map_name="Open Field",
        party_a_key="longbow_archer_a",
        party_b_key="swordsman_b",
        description="Longbow archer (kiting AI) vs light swordsman.",
    ),
    "bear": Preset(
        key="bear",
        map_name="Small Room",
        party_a_key="two_warriors_a",
        party_b_key="bear_b",
        description="Two warriors vs a black bear in close quarters.",
    ),
}


def _make_preset_frontend(preset: Preset, base: TerminalFrontend):
    """Wrap a terminal frontend so map/party choices use the preset
    while everything else stays interactive."""

    class _PresetFrontend:
        # Setup — preset values
        def choose_map(self, maps):
            for m in maps:
                if m.name == preset.map_name:
                    return m
            raise SystemExit(
                f"Preset {preset.key!r} expects a map named "
                f"{preset.map_name!r}, but it wasn't found. "
                f"Available: {[m.name for m in maps]}"
            )

        def choose_party(self, templates, side):
            key = preset.party_a_key if side == "A" else preset.party_b_key
            for t in templates:
                if t.key == key:
                    return t
            raise SystemExit(
                f"Preset {preset.key!r} expects party template {key!r} "
                f"for side {side}, but it wasn't found."
            )

        # Everything else — delegate to the wrapped terminal frontend.
        def choose_human_controlled(self, creatures):
            return base.choose_human_controlled(creatures)

        def choose_conditions(self):
            return base.choose_conditions()

        def prompt_action(self, actor, options, ctx):
            return base.prompt_action(actor, options, ctx)

        def prompt_reaction(self, actor, attacker, ctx):
            return base.prompt_reaction(actor, attacker, ctx)

        def on_round_start(self, ctx):
            return base.on_round_start(ctx)

        def on_action_resolved(self, actor, action, ctx):
            return base.on_action_resolved(actor, action, ctx)

        def on_combat_end(self, result, ctx):
            return base.on_combat_end(result, ctx)

    return _PresetFrontend()


def main() -> int:
    ap = argparse.ArgumentParser(prog="combat_sim.ui")
    ap.add_argument("--scenario", "-s",
                    help=f"Skip map+party choice and load a preset. "
                         f"Available: {', '.join(PRESETS)}.")
    ap.add_argument("--list-presets", action="store_true",
                    help="List available preset scenarios and exit.")
    ap.add_argument("--seed", type=int, default=None,
                    help="Random seed for reproducibility.")
    ap.add_argument("--live", action="store_true",
                    help="Single-screen mode: the combat view redraws in "
                         "place instead of scrolling, and the full "
                         "play-by-play goes to the --log file.")
    ap.add_argument("--log", default="combat.log",
                    help="Path for the play-by-play log in --live mode "
                         "(default: combat.log).")
    ap.add_argument("--iso", action="store_true",
                    help="Graphical isometric frontend (pygame window). "
                         "Map/party/human selection still happen in the "
                         "terminal; combat plays in the window.")
    ap.add_argument("--speed", type=float, default=0.4,
                    help="Seconds each AI turn pauses in --iso mode so "
                         "moves are watchable (default 0.4).")
    args = ap.parse_args()

    if args.list_presets:
        for p in PRESETS.values():
            print(f"  {p.key}: {p.description}")
            print(f"    map={p.map_name}, "
                  f"A={p.party_a_key}, B={p.party_b_key}")
        return 0

    if args.scenario and args.scenario not in PRESETS:
        print(f"Unknown preset {args.scenario!r}. Known: {list(PRESETS)}")
        return 2

    # Graphical isometric frontend: sim runs on a worker thread, pygame
    # owns the main thread. Setup prompts still use the terminal (the
    # window shows a splash until the first round).
    if args.iso:
        from .iso import IsoFrontend, run_iso_game
        iso = IsoFrontend(speed=args.speed)
        game_frontend = (_make_preset_frontend(PRESETS[args.scenario], iso)
                         if args.scenario else iso)
        try:
            return run_iso_game(iso, game_frontend, Registry(), seed=args.seed)
        except (KeyboardInterrupt, EOFError):
            print("\nAborted.")
            return 130

    base = LiveTerminalFrontend(log_path=args.log) if args.live \
        else TerminalFrontend()
    if args.scenario:
        frontend = _make_preset_frontend(PRESETS[args.scenario], base)
    else:
        frontend = base

    # ``base`` owns the alternate screen + logfile in live mode; the
    # context manager restores the terminal even on Ctrl-C. The preset
    # wrapper delegates render hooks to ``base``, so its lifecycle still
    # drives the live screen.
    lifecycle = base if isinstance(base, LiveTerminalFrontend) \
        else nullcontext()
    try:
        with lifecycle:
            run_game(frontend, Registry(), seed=args.seed)
    except (KeyboardInterrupt, EOFError):
        print("\nAborted.")
        return 130
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
