#!/usr/bin/env python3
"""Step 2 — rank class options for the rolled abilities.

Prints every class with a heuristic fit score (primary abilities double),
the best single two-score swap that would improve that fit, and the class's
careers with their Status. The rulebook has no roll tables; use --roll to
pick a class and career at random instead of choosing.
"""
import argparse
import itertools
from pathlib import Path

from vflib import (ABILITIES, CLASS_HINTS, CLASSES,
                   Dice, FORCED_ALIGNMENT, careers_of, load_class, load_state,
                   modifier, parse_career)


def fit_score(mods: dict, klass: str) -> int:
    h = CLASS_HINTS[klass]
    return 2 * sum(mods[a] for a in h["primary"]) + sum(mods[a] for a in h["secondary"])


def best_swap(scores: dict, klass: str):
    base = fit_score({a: modifier(s) for a, s in scores.items()}, klass)
    best = None
    for a, b in itertools.combinations(ABILITIES, 2):
        swapped = dict(scores)
        swapped[a], swapped[b] = swapped[b], swapped[a]
        gain = fit_score({k: modifier(v) for k, v in swapped.items()}, klass) - base
        if gain > 0 and (best is None or gain > best[2]):
            best = (a, b, gain)
    return best


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--file", type=Path, default=Path("character.json"))
    ap.add_argument("--roll", action="store_true",
                    help="pick a class and one of its careers at random")
    ap.add_argument("--seed", type=int)
    args = ap.parse_args()

    state = load_state(args.file)
    scores = {a: v["score"] for a, v in state["abilities"].items()}
    mods = {a: v["mod"] for a, v in state["abilities"].items()}

    print("Abilities: " + ", ".join(f"{a} {scores[a]} ({mods[a]:+d})" for a in ABILITIES))
    print()

    if args.roll:
        dice = Dice(args.seed)
        klass = CLASSES[dice.roll(1, len(CLASSES)) - 1]
        table = careers_of(klass)
        if table:
            career = table[dice.roll(1, len(table)) - 1].stem
            print(f"Picked class {klass}; career {career}")
            print(f"Apply with: apply_class.py --file {args.file} "
                  f"--class '{klass}' --career '{career}'")
        else:
            print(f"Picked class {klass}; {klass} has no careers")
            print(f"Apply with: apply_class.py --file {args.file} "
                  f"--class '{klass}' --status brass|silver|gold")
        return

    rows = []
    for klass in CLASSES:
        info = load_class(klass)
        h = CLASS_HINTS[klass]
        fit = fit_score(mods, klass)
        swap = None if state.get("swap_used") else best_swap(scores, klass)
        careers = []
        for p in careers_of(klass):
            status = parse_career(p)["status"]
            careers.append(f"{p.stem} [{status or '?'}]")
        rows.append((fit, klass, info, h, swap, careers))

    rows.sort(key=lambda r: (-(r[0] + (r[4][2] if r[4] else 0)), -r[0]))
    for fit, klass, info, h, swap, careers in rows:
        keys = "/".join(h["primary"]) + ("; " + "/".join(h["secondary"]) if h["secondary"] else "")
        line = (f"{fit:+d}  {klass:<11} Wounds {info['wounds']}, Stamina {info['stamina_die']}"
                f"  key: {keys}")
        if klass in FORCED_ALIGNMENT:
            line += f"  [must be {FORCED_ALIGNMENT[klass]}]"
        print(line)
        if swap:
            a, b, gain = swap
            print(f"      swap {a} <-> {b} for {fit + gain:+d}")
        print(f"      note: {h['note']}")
        print(f"      careers: {', '.join(careers) if careers else '(none written yet)'}")
    print("\nStatus tags: Gold starts with 1d6 gp, Silver 2d6x10 sp, Brass 10d6x10 bp.")
    print("Next: apply_class.py --class C --career R [--swap A B]")


if __name__ == "__main__":
    main()
