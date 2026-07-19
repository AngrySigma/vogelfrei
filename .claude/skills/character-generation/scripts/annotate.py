#!/usr/bin/env python3
"""Record agent decisions on the character: notes, skills, small field edits.

Used mainly by the class-specific skills (e.g. class-warrior) after the core
generation is done.

  annotate.py --note "Squire: 0-level henchman, unnamed yet"
  annotate.py --skill "Bushcraft=2" --skill "Climb=1"
  annotate.py --set ws=2 --set enc_adjust=-1
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
    args = ap.parse_args()

    state = load_state(args.file)
    for note in args.note:
        state["notes"].append(note)
        log(state, f"Note: {note}")
    for spec in args.skill:
        name, _, rating = spec.partition("=")
        if not rating.isdigit():
            die(f"bad --skill '{spec}', expected Name=N")
        state["skills"][name.strip()] = int(rating)
        log(state, f"Skill: {name.strip()} {rating}-in-6")
    for spec in args.set:
        key, _, value = spec.partition("=")
        key = key.strip()
        if key not in SETTABLE:
            die(f"field '{key}' is not settable here (allowed: {', '.join(SETTABLE)})")
        try:
            state[key] = SETTABLE[key](value.strip())
        except ValueError:
            die(f"bad value for {key}: '{value}'")
        log(state, f"Set {key} = {state[key]}")
    save_state(args.file, state)


if __name__ == "__main__":
    main()
