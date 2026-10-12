#!/usr/bin/env python3
"""Step 5 — buy equipment, with price and budget validation.

Prices are parsed from the tables under docs/Equipment/ — browse those pages
to decide WHAT to buy; use this script to record it, so cost, budget and
encumbrance stay honest. New characters buy at the cheaper of the City and
Rural price (docs/Character/Starting Possessions.md); --market forces one.

  buy.py catalog [CATEGORY]     list categories, or the items of one
  buy.py add ITEM [--qty N] [--market city|rural] [--price 5sp] [--free]
  buy.py remove ITEM [--qty N]
  buy.py list
"""
import argparse
from pathlib import Path

from vflib import (die, encumbrance, equipment_db, find_items, fmt_money,
                   load_state, log, parse_money, save_state)


def entry_for(state, name):
    for e in state["inventory"]:
        if e["name"].lower() == name.lower():
            return e
    return None


def cmd_catalog(db, category):
    if not category:
        cats = {}
        for i in db:
            cats[i.category] = cats.get(i.category, 0) + 1
        print("Categories (see docs/Equipment/ for full descriptions):")
        for c, n in sorted(cats.items()):
            print(f"  {c:<16} {n} items")
        return
    rows = [i for i in db if i.category.lower().startswith(category.lower())]
    if not rows:
        die(f"no category matching '{category}'")
    for i in rows:
        price = " / ".join(fmt_money(p) if p is not None else "-"
                           for p in (i.city_bp, i.rural_bp))
        extra = "; ".join(f"{k} {v}" for k, v in i.props.items())
        flag = {"light": " [non-enc]", "oversize": " [oversize]"}.get(i.enc, "")
        print(f"  {i.display:<34} {price:<18} {extra}{flag}")


def resolve(db, query):
    matches = find_items(db, query)
    if not matches:
        die(f"'{query}' not found in the equipment tables. If the item really exists "
            f"in docs/Equipment, record it with --price (read the price off the page).", 2)
    displays = {m.display for m in matches}
    if len(displays) > 1:
        print(f"'{query}' is ambiguous:")
        for m in matches:
            print(f"  {m.display}  ({m.category})")
        raise SystemExit(2)
    return matches[0]


def cmd_add(state, db, args):
    if args.price or args.free:
        unit = 0 if args.free else parse_money(args.price)
        matches = find_items(db, args.item)
        item = matches[0] if len({m.display for m in matches}) == 1 else None
        name, category = (item.display, item.category) if item else (args.item, "Custom")
        enc = item.enc if item else ("light" if args.non_encumbering else "normal")
        props = dict(item.props) if item else {}
        market = "free" if args.free else "override"
    else:
        item = resolve(db, args.item)
        name, category, enc, props = item.display, item.category, item.enc, dict(item.props)
        prices = {"city": item.city_bp, "rural": item.rural_bp}
        if args.market:
            unit = prices[args.market]
            if unit is None:
                die(f"{name} has no {args.market} price; available: "
                    + ", ".join(k for k, v in prices.items() if v is not None))
            market = args.market
        else:
            avail = {k: v for k, v in prices.items() if v is not None}
            if not avail:
                die(f"{name} has no listed price (cell is '-'); use --price or --free")
            market, unit = min(avail.items(), key=lambda kv: kv[1])

    cost = unit * args.qty
    money = state.get("money_bp")
    if money is None:
        die("no starting money yet — run apply_class.py first")
    if cost > money:
        die(f"cannot afford {args.qty}x {name}: costs {fmt_money(cost)}, "
            f"only {fmt_money(money)} left")

    existing = entry_for(state, name)
    if existing and existing.get("unit_bp") == unit:
        existing["qty"] += args.qty
    else:
        state["inventory"].append({"name": name, "qty": args.qty, "unit_bp": unit,
                                   "market": market, "category": category,
                                   "enc": enc, "props": props})
    state["money_bp"] = money - cost
    log(state, f"Bought {args.qty}x {name} @ {fmt_money(unit)} ({market}) "
               f"-> {fmt_money(state['money_bp'])} left")


def cmd_remove(state, args):
    e = entry_for(state, args.item)
    if not e:
        matches = [x["name"] for x in state["inventory"]
                   if args.item.lower() in x["name"].lower()]
        if len(matches) == 1:
            e = entry_for(state, matches[0])
        else:
            die(f"'{args.item}' is not in the inventory"
                + (f" (matches: {', '.join(matches)})" if matches else ""))
    qty = min(args.qty, e["qty"])
    e["qty"] -= qty
    state["money_bp"] += e["unit_bp"] * qty
    if e["qty"] == 0:
        state["inventory"].remove(e)
    log(state, f"Removed {qty}x {e['name']}, refunded {fmt_money(e['unit_bp'] * qty)} "
               f"-> {fmt_money(state['money_bp'])} left")


def cmd_list(state):
    total = 0
    for e in state["inventory"]:
        line_bp = e["unit_bp"] * e["qty"]
        total += line_bp
        flag = {"light": " [non-enc]", "oversize": " [oversize]"}.get(e["enc"], "")
        print(f"  {e['qty']}x {e['name']:<30} {fmt_money(line_bp):<12} ({e['category']}){flag}")
    print(f"\n  spent {fmt_money(total)}, remaining {fmt_money(state.get('money_bp', 0))}")
    enc = encumbrance(state, worn_armor=None)
    print(f"  encumbrance so far (armour not yet counted): {enc['points']} points "
          f"-> {enc['label']}")


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--file", type=Path, default=Path("character.json"))
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("catalog")
    p.add_argument("category", nargs="?")
    p = sub.add_parser("add")
    p.add_argument("item")
    p.add_argument("--qty", type=int, default=1)
    p.add_argument("--market", choices=["city", "rural"])
    p.add_argument("--price", help="manual unit price, e.g. '5sp' (for unparsed items)")
    p.add_argument("--free", action="store_true", help="no cost (e.g. starting clothes)")
    p.add_argument("--non-encumbering", action="store_true",
                   help="with --price: mark the custom item non-encumbering")
    p = sub.add_parser("remove")
    p.add_argument("item")
    p.add_argument("--qty", type=int, default=1)
    sub.add_parser("list")
    args = ap.parse_args()

    db = equipment_db()
    if args.cmd == "catalog":
        cmd_catalog(db, args.category)
        return
    state = load_state(args.file)
    if args.cmd == "add":
        cmd_add(state, db, args)
    elif args.cmd == "remove":
        cmd_remove(state, args)
    elif args.cmd == "list":
        cmd_list(state)
        return
    save_state(args.file, state)


if __name__ == "__main__":
    main()
