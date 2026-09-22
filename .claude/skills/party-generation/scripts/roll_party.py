#!/usr/bin/env python3
"""Party step 1 — roll every character's abilities at once and tabulate the fit.

Creates one character state file per PC (pc1.json … pcN.json) in --dir, each
holding nothing but the rolled ability scores, then prints:

  * the six scores per PC,
  * a class-fit matrix over the allowed class pool,
  * each PC's strongest classes with the one swap that would improve them, and
  * which careers of those classes are fully written in the rulebook.

Assignment itself is a judgement call — this only lays out the evidence.
"""
import argparse
import itertools
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve()
sys.path.insert(0, str(HERE.parents[2] / "character-generation" / "scripts"))

from vflib import (ABILITIES, CLASS_HINTS, CLASSES, Dice, die, load_class,  # noqa: E402
                   modifier, new_state, repo_root, save_state)

# Demihuman classes, for --humans-only (docs/Character/Classes/).
DEMIHUMAN = {"Dwarf", "Halfling", "High Elf", "Wood Elf"}


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


def complete_careers() -> dict:
    """{class: [career names the rulebook actually finished]} from careers.json."""
    path = repo_root() / "docs" / "data" / "careers.json"
    if not path.exists():
        return {}
    rows = json.loads(path.read_text(encoding="utf-8"))["careers"]
    out = {}
    for r in rows:
        if r.get("complete"):
            out.setdefault(r["class"], []).append(r["name"])
    return {k: sorted(v) for k, v in out.items()}


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dir", type=Path, required=True,
                    help="party directory, e.g. characters/tower-of-the-stargazer")
    ap.add_argument("--count", type=int, required=True, help="how many characters")
    ap.add_argument("--classes", help="comma-separated class pool (default: all twelve)")
    ap.add_argument("--humans-only", action="store_true",
                    help="drop Dwarf, Halfling, High Elf and Wood Elf from the pool")
    ap.add_argument("--reroll-unsuitable", action="store_true",
                    help="reroll any array whose modifier total is negative")
    ap.add_argument("--seed", type=int)
    ap.add_argument("--force", action="store_true", help="overwrite existing pcN.json")
    args = ap.parse_args()

    if args.count < 1:
        die("--count must be at least 1")

    pool = CLASSES
    if args.classes:
        want = [c.strip() for c in args.classes.split(",") if c.strip()]
        unknown = [c for c in want if c not in CLASSES]
        if unknown:
            die(f"unknown class(es): {', '.join(unknown)} (options: {', '.join(CLASSES)})")
        pool = [c for c in CLASSES if c in want]
    if args.humans_only:
        pool = [c for c in pool if c not in DEMIHUMAN]
    if not pool:
        die("the class pool is empty")

    dice = Dice(args.seed)
    finished = complete_careers()

    rolled = []
    for i in range(1, args.count + 1):
        path = args.dir / f"pc{i}.json"
        if path.exists() and not args.force:
            die(f"{path} already exists; use --force to reroll the whole party")
        for attempt in range(1, 101):
            scores = {a: dice.roll(3, 6) for a in ABILITIES}
            total = sum(modifier(s) for s in scores.values())
            if total >= 0 or not args.reroll_unsuitable:
                break
        state = new_state()
        state["abilities"] = {a: {"score": s, "mod": modifier(s)}
                              for a, s in scores.items()}
        state["party_slot"] = f"pc{i}"
        state["log"].append(
            f"Rolled 3d6 in order (attempt {attempt}): "
            + ", ".join(f"{a} {s}" for a, s in scores.items()))
        save_state(path, state)
        rolled.append((f"pc{i}", path, scores, total))

    # --- the arrays -------------------------------------------------------
    print(f"Rolled {len(rolled)} characters into {args.dir}/\n")
    head = "| PC | " + " | ".join(a[:4] for a in ABILITIES) + " | mods |"
    print(head)
    print("|" + " --- |" * (len(ABILITIES) + 2))
    for slot, _, scores, total in rolled:
        cells = " | ".join(f"{scores[a]} ({modifier(scores[a]):+d})" for a in ABILITIES)
        print(f"| {slot} | {cells} | {total:+d} |")
        if total < 0:
            print(f"|    | UNSUITABLE by the book — {slot} may be discarded and rerolled "
                  "| | | | | | |")

    # --- the fit matrix ---------------------------------------------------
    print(f"\nClass fit (higher is better; pool of {len(pool)}):\n")
    width = max(len(c) for c in pool) + 1
    print("| PC | " + " | ".join(pool) + " |")
    print("|" + " --- |" * (len(pool) + 1))
    for slot, _, scores, _ in rolled:
        mods = {a: modifier(s) for a, s in scores.items()}
        print(f"| {slot} | " + " | ".join(f"{fit_score(mods, c):+d}" for c in pool) + " |")

    # --- per-PC shortlist -------------------------------------------------
    print("\nStrongest fits per character (swap = the one allowed two-score swap):\n")
    for slot, _, scores, _ in rolled:
        mods = {a: modifier(s) for a, s in scores.items()}
        ranked = sorted(pool, key=lambda c: -fit_score(mods, c))[:4]
        print(f"  {slot}:")
        for c in ranked:
            sw = best_swap(scores, c)
            swap = f"  [swap {sw[0]} <-> {sw[1]} for +{sw[2]}]" if sw else ""
            note = CLASS_HINTS[c]["note"]
            print(f"    {fit_score(mods, c):+d}  {c:<{width}}{swap}")
            print(f"        {note}")

    # --- careers ----------------------------------------------------------
    print("\nCareers fully written in the rulebook (docs/data/careers.json):\n")
    for c in pool:
        names = finished.get(c, [])
        if c == "Rogue":
            print(f"  {c:<{width}} no careers by design — pass --status to apply_class.py")
        elif names:
            print(f"  {c:<{width}} {', '.join(names)}")
        else:
            print(f"  {c:<{width}} none complete — every career page is still a stub")
    print("\nStub careers still work: they need --status brass|silver|gold, and their\n"
          "traits are pending rulebook content.")

    # --- wounds, for party durability planning ----------------------------
    print("\nWounds dice by class (Toughness modifier is added once at level 1):\n")
    for c in pool:
        info = load_class(c)
        print(f"  {c:<{width}} {info['wounds_die']} (min {info['wounds_min']}), "
              f"Stamina {info['stamina_die'] or '—'}, WS +{info['ws']} / BS +{info['bs']}")

    print(f"\nNext: decide class + career + concept per PC, write the briefs, then run\n"
          f"one character-generation pass per PC on {args.dir}/pcN.json.")


if __name__ == "__main__":
    main()
