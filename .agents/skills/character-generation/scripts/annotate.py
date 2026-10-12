#!/usr/bin/env python3
"""Record agent decisions on the character: notes, skills, small field edits.

Used mainly by the class-specific skills (e.g. class-warrior) after the core
generation is done.

  annotate.py --note "Squire: 0-level henchman, unnamed yet"
  annotate.py --skill "Bushcraft=2" --skill "Climb=1" --spend 2
  annotate.py --set ws=2 --set enc_adjust=-1

--skill records a FINAL rating (N-in-6) and does not touch the skill-point
pool, because a rating does not say how many points bought it. Pass --spend N
alongside it to draw the points down, or the sheet keeps reporting them as
unspent.
"""
import argparse
from pathlib import Path

from vflib import die, load_state, log, save_state

SETTABLE = {"name": str, "alignment": str, "ws": int, "bs": int,
            "skill_points": int, "enc_adjust": int, "culture": str}


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--file", type=Path, default=Path("character.json"))
    ap.add_argument("--note", action="append", default=[])
    ap.add_argument("--skill", action="append", default=[], metavar="NAME=RATING",
                    help="record a skill at N-in-6")
    ap.add_argument("--set", action="append", default=[], metavar="KEY=VALUE",
                    help=f"set a field ({', '.join(SETTABLE)})")
    ap.add_argument("--spend", type=int, metavar="N",
                    help="draw N points out of the skill-point pool (use with --skill)")
    args = ap.parse_args()

    state = load_state(args.file)

    # Validate the whole batch BEFORE applying or printing any of it. These
    # calls carry several --note/--skill/--set at once, and a single bad one
    # used to die after the earlier items had already printed their
    # confirmations — so the batch looked applied while nothing was saved.
    skills = []
    for spec in args.skill:
        name, _, rating = spec.partition("=")
        if not rating.strip().isdigit():
            die(f"bad --skill '{spec}', expected Name=N")
        skills.append((name.strip(), int(rating)))

    if args.spend is not None:
        if args.spend < 0:
            die("--spend takes a positive number of points")
        pool = state.get("skill_points") or 0
        if args.spend > pool:
            die(f"cannot spend {args.spend} skill point(s): only {pool} in the pool")

    sets = []
    for spec in args.set:
        key, sep, value = spec.partition("=")
        key = key.strip()
        if not sep:
            die(f"bad --set '{spec}', expected KEY=VALUE")
        if key not in SETTABLE:
            die(f"field '{key}' is not settable here (allowed: {', '.join(SETTABLE)})")
        try:
            sets.append((key, SETTABLE[key](value.strip())))
        except ValueError:
            die(f"bad value for {key}: '{value}'")

    # Everything checked out; now apply.
    for note in args.note:
        state["notes"].append(note)
        log(state, f"Note: {note}")
    for name, rating in skills:
        state["skills"][name] = rating
        log(state, f"Skill: {name} {rating}-in-6")
    if args.spend is not None:
        state["skill_points"] = (state.get("skill_points") or 0) - args.spend
        log(state, f"Spent {args.spend} skill point(s); {state['skill_points']} left")
    for key, value in sets:
        state[key] = value
        log(state, f"Set {key} = {value}")
    save_state(args.file, state)


if __name__ == "__main__":
    main()
