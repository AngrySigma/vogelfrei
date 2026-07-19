#!/usr/bin/env python3
"""Step 4a — roll sex, age, height and build.

The rulebook has no tables for these, so the ranges below are workflow
conventions: humans come of age in their late teens, book-learned careers
start older, demihumans are far older than any human.
"""
import argparse
from pathlib import Path

from vflib import Dice, die, load_state, log, save_state

AGE = {  # class -> (base, dice as (n, sides))
    "Dwarf": (30, (4, 10)),
    "Halfling": (20, (2, 10)),
    "High Elf": (80, (4, 20)),
    "Wood Elf": (80, (4, 20)),
}
LEARNED = {"Magic-User", "Cleric", "Academic"}  # extra 1d8 years of study

HEIGHT = {  # class -> (base inches by sex, dice)
    "Dwarf": ({"male": 48, "female": 46}, (2, 4)),
    "Halfling": ({"male": 34, "female": 33}, (2, 4)),
    "High Elf": ({"male": 64, "female": 62}, (2, 6)),
    "Wood Elf": ({"male": 64, "female": 62}, (2, 6)),
}
HUMAN_HEIGHT = ({"male": 62, "female": 59}, (2, 6))

BUILDS = ["gaunt", "wiry", "lean", "average", "stocky", "broad", "heavyset", "towering"]


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--file", type=Path, default=Path("character.json"))
    ap.add_argument("--sex", choices=["male", "female"])
    ap.add_argument("--age", type=int)
    ap.add_argument("--seed", type=int)
    args = ap.parse_args()

    state = load_state(args.file)
    klass = state.get("class")
    if not klass:
        die("apply a class first (age and height depend on it)")
    dice = Dice(args.seed)

    sex = args.sex or ("male" if dice.roll(1, 2) == 1 else "female")
    if args.age:
        age = args.age
    else:
        base, (n, s) = AGE.get(klass, (15, (2, 8)))
        age = base + dice.roll(n, s)
        if klass in LEARNED:
            age += dice.roll(1, 8)

    bases, (hn, hs) = HEIGHT.get(klass, HUMAN_HEIGHT)
    inches = bases[sex] + dice.roll(hn, hs)
    height = f"{inches // 12}'{inches % 12}\""
    build = BUILDS[dice.roll(1, len(BUILDS)) - 1]

    state["bio"] = {"sex": sex, "age": age, "height": height, "build": build}
    log(state, f"Bio: {sex}, age {age}, {height}, {build} build")
    save_state(args.file, state)


if __name__ == "__main__":
    main()
