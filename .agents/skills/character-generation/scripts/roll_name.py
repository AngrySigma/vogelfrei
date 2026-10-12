#!/usr/bin/env python3
"""Step 4b — propose or set the character's name.

Built-in period name lists cover the default setting cultures (17th-century
England, Wales, Scotland, Ireland). For other cultures the script tries the
free randomuser.me API (mapped by nationality); when neither source fits it
exits with code 3 — the generating agent must then invent a fitting name
itself and record it with --set.

Default action lists candidates; --pick records the first one; --set NAME
records an exact name.
"""
import argparse
import json
import urllib.request
from pathlib import Path

from vflib import Dice, die, load_state, log, save_state

NAMES = {
    "england-17c": {
        "male": ["John", "Thomas", "William", "Richard", "Robert", "Edward", "Henry",
                 "George", "Francis", "James", "Samuel", "Nathaniel", "Josiah",
                 "Edmund", "Walter", "Matthew", "Nicholas", "Roger", "Humphrey", "Gilbert"],
        "female": ["Elizabeth", "Mary", "Anne", "Margaret", "Alice", "Jane", "Agnes",
                   "Katherine", "Eleanor", "Joan", "Dorothy", "Susanna", "Grace",
                   "Prudence", "Mercy", "Charity", "Temperance", "Constance", "Faith", "Honor"],
        "surname": ["Smith", "Cooper", "Fletcher", "Turner", "Walker", "Wright", "Baker",
                    "Carter", "Mason", "Ward", "Webb", "Sherwood", "Ashworth", "Whitfield",
                    "Holloway", "Fairfax", "Hargreaves", "Thatcher", "Bowyer", "Sadler",
                    "Tanner", "Pettigrew", "Blackwood", "Marlowe", "Aldridge", "Winthrop"],
    },
    "wales-17c": {
        "male": ["Rhys", "Owain", "Gwilym", "Dafydd", "Morgan", "Evan", "Hywel",
                 "Llewellyn", "Cadoc", "Ieuan"],
        "female": ["Gwen", "Angharad", "Nest", "Rhiannon", "Mared", "Catrin", "Eluned"],
        "surname": ["ap Rhys", "Jones", "Evans", "Davies", "Griffiths", "Llewellyn",
                    "Vaughan", "Powell", "Pritchard", "Bowen"],
    },
    "scotland-17c": {
        "male": ["Alasdair", "Ewan", "Duncan", "Malcolm", "Angus", "Hamish", "Callum",
                 "Fergus", "Gregor", "Lachlan"],
        "female": ["Moira", "Isobel", "Fiona", "Ailsa", "Mairi", "Elspeth", "Sorcha"],
        "surname": ["MacLeod", "MacDonald", "Campbell", "Stewart", "Fraser", "MacGregor",
                    "Sinclair", "Douglas", "Buchanan", "Armstrong"],
    },
    "ireland-17c": {
        "male": ["Seamus", "Padraig", "Cormac", "Donal", "Eoin", "Fionn", "Niall",
                 "Brendan", "Ciaran", "Ronan"],
        "female": ["Aoife", "Brigid", "Maeve", "Siobhan", "Niamh", "Grainne", "Deirdre"],
        "surname": ["O'Brien", "O'Connor", "O'Neill", "Kavanagh", "Murphy", "Byrne",
                    "Doyle", "Flanagan", "MacCarthy", "Nolan"],
    },
}
ALIASES = {
    "england": "england-17c", "english": "england-17c", "uk": "england-17c",
    "britain": "england-17c", "default": "england-17c",
    "wales": "wales-17c", "welsh": "wales-17c",
    "scotland": "scotland-17c", "scottish": "scotland-17c",
    "ireland": "ireland-17c", "irish": "ireland-17c",
}
# randomuser.me nationality codes for cultures outside the built-in lists.
NAT_CODES = {
    "france": "fr", "french": "fr", "germany": "de", "german": "de",
    "spain": "es", "spanish": "es", "netherlands": "nl", "dutch": "nl",
    "denmark": "dk", "danish": "dk", "norway": "no", "norwegian": "no",
    "finland": "fi", "finnish": "fi", "switzerland": "ch", "serbia": "rs",
    "turkey": "tr", "turkish": "tr", "ukraine": "ua", "ukrainian": "ua",
    "iran": "ir", "persian": "ir", "india": "in", "indian": "in",
    "mexico": "mx", "brazil": "br", "usa": "us", "america": "us",
}


def api_candidates(nat: str, sex: str | None, count: int) -> list[str]:
    url = f"https://randomuser.me/api/?results={count}&nat={nat}&inc=name"
    if sex:
        url += f"&gender={sex}"
    with urllib.request.urlopen(url, timeout=10) as resp:
        data = json.load(resp)
    return [f"{r['name']['first']} {r['name']['last']}" for r in data["results"]]


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--file", type=Path, default=Path("character.json"))
    ap.add_argument("--culture", default="england-17c")
    ap.add_argument("--sex", choices=["male", "female"])
    ap.add_argument("--count", type=int, default=6)
    ap.add_argument("--pick", action="store_true", help="record the first candidate")
    ap.add_argument("--set", dest="set_name", metavar="NAME", help="record this exact name")
    ap.add_argument("--seed", type=int)
    args = ap.parse_args()

    state = load_state(args.file)
    culture = ALIASES.get(args.culture.strip().lower(), args.culture.strip().lower())
    sex = args.sex or state.get("bio", {}).get("sex")

    if args.set_name:
        state["name"] = args.set_name
        state["culture"] = culture
        log(state, f"Name set: {args.set_name} ({culture})")
        save_state(args.file, state)
        return

    if culture in NAMES:
        dice = Dice(args.seed)
        pool = NAMES[culture]
        firsts = pool[sex] if sex in pool else pool["male"] + pool["female"]
        candidates = []
        while len(candidates) < args.count:
            name = (f"{firsts[dice.roll(1, len(firsts)) - 1]} "
                    f"{pool['surname'][dice.roll(1, len(pool['surname'])) - 1]}")
            if name not in candidates:
                candidates.append(name)
    else:
        nat = NAT_CODES.get(culture)
        if not nat:
            die(f"no name source for culture '{args.culture}': not a built-in list and no "
                f"API nationality mapping. Invent a period-appropriate name yourself and "
                f"record it with --set 'Name'.", code=3)
        try:
            candidates = api_candidates(nat, sex, args.count)
        except Exception as e:  # offline, blocked, API down...
            die(f"randomuser.me unreachable ({e}). Invent a fitting name for culture "
                f"'{args.culture}' yourself and record it with --set 'Name'.", code=3)

    for c in candidates:
        print(f"  {c}")
    if args.pick:
        state["name"] = candidates[0]
        state["culture"] = culture
        log(state, f"Name picked: {candidates[0]} ({culture})")
        save_state(args.file, state)
    else:
        print("\nRecord one with --pick (first) or --set 'Name'.")


if __name__ == "__main__":
    main()
