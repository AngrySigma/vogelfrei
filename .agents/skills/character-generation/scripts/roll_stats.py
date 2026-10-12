#!/usr/bin/env python3
"""Step 1 — roll 3d6 in order for the six ability scores.

Creates the character state file. By the book a player MAY discard a
character whose ability modifiers sum below zero; pass --reroll-unsuitable
to do that automatically (recommended for quick generation).
"""
import argparse
from pathlib import Path

from vflib import ABILITIES, Dice, die, log, modifier, new_state, save_state


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--file", type=Path, default=Path("character.json"))
    ap.add_argument("--seed", type=int)
    ap.add_argument("--reroll-unsuitable", action="store_true",
                    help="reroll automatically while the modifier total is negative")
    ap.add_argument("--force", action="store_true", help="overwrite an existing file")
    args = ap.parse_args()

    if args.file.exists() and not args.force:
        die(f"{args.file} already exists; use --force to start over")

    dice = Dice(args.seed)
    for attempt in range(1, 101):
        scores = {a: dice.roll(3, 6) for a in ABILITIES}
        total = sum(modifier(s) for s in scores.values())
        if total >= 0 or not args.reroll_unsuitable:
            break

    state = new_state()
    state["abilities"] = {a: {"score": s, "mod": modifier(s)} for a, s in scores.items()}
    log(state, f"Rolled 3d6 in order (attempt {attempt}): "
               + ", ".join(f"{a} {s}" for a, s in scores.items()))

    print()
    for a, s in scores.items():
        print(f"  {a:<12} {s:>2}  ({modifier(s):+d})")
    print(f"  {'total mods':<12}     ({total:+d})")
    if total < 0:
        print("\n  UNSUITABLE by the book (modifier total below zero) — the player may")
        print("  discard and reroll, or keep it for the challenge.")
    print("\n  One swap of two ability scores is allowed, spent at class choice")
    print("  (apply_class.py --swap A B). Next: class_options.py")

    save_state(args.file, state)
    print(f"\nwrote {args.file}")


if __name__ == "__main__":
    main()
