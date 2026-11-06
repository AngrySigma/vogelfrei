#!/usr/bin/env python3
"""Score a Markdown extraction page-by-page against the PDF's raw glyph stream.

Aggregate recall hides exactly the failure that matters. When a two-column
layout model clips table cells at the column boundary, it loses maybe 60 words
out of 8,000 -- 99.3% recall, which looks fine and is not. Scoring each page
separately puts those 60 words against that page's ~700, and the bad page
drops to 0.91 while every other page stays at 1.00. The floor is the signal,
not the mean.

The reference is `page.get_text("text")`: the same glyphs the layout model saw,
with no column detection, table reconstruction or reading-order logic applied.
Anything present there and absent from the Markdown was dropped by layout
analysis, which is the error class worth catching.

Usage: python verify_extraction.py BOOK.pdf extracted.md [--floor 0.95]
       python verify_extraction.py BOOK.pdf --chunks chunks.json
"""
import argparse
import re
import sys
from collections import Counter

import pymupdf

WORD = re.compile(r"[0-9a-z']+")


def bag(text):
    return Counter(WORD.findall(text.lower()))


def page_recall(ref_text, cand_bag):
    ref = bag(ref_text)
    total = sum(ref.values())
    if total < 25:                     # art plates, title pages: nothing to score
        return None, []
    missing = []
    lost = 0
    for w, n in ref.items():
        gap = n - cand_bag.get(w, 0)
        if gap > 0:
            lost += gap
            missing.append((gap, w))
    missing.sort(reverse=True)
    return 1.0 - lost / total, [w for _, w in missing[:8]]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pdf")
    ap.add_argument("markdown")
    ap.add_argument("--floor", type=float, default=0.995,
                    help="minimum acceptable per-page recall; a clean "
                         "born-digital page scores exactly 1.000, so the "
                         "margin here is small deliberately")
    ap.add_argument("--show", type=int, default=10)
    a = ap.parse_args()

    md_bag = bag(open(a.markdown, errors="ignore").read())
    doc = pymupdf.open(a.pdf)

    # The Markdown is one stream, so score each page's words against the whole
    # document bag. That cannot detect *reordering*, only loss -- which is the
    # point: reordering is cosmetic, loss is not.
    rows = []
    for i, page in enumerate(doc):
        r, missing = page_recall(page.get_text("text"), md_bag)
        if r is not None:
            rows.append((i + 1, r, missing))
    doc.close()

    if not rows:
        print("no scoreable pages (no text layer?)")
        return 2

    rows.sort(key=lambda t: t[1])
    mean = sum(r for _, r, _ in rows) / len(rows)
    print(f"pages scored: {len(rows)}   mean recall {mean:.3f}   "
          f"worst page {rows[0][1]:.3f} (p{rows[0][0]})")

    bad = [r for r in rows if r[1] < a.floor]
    if bad:
        print(f"\n{len(bad)} page(s) below floor {a.floor}:")
        for pno, r, missing in bad[:a.show]:
            print(f"  p{pno:>4}  recall {r:.3f}  dropped: {', '.join(missing)}")
        print("\nOpen those pages and look for tables, sidebars, or marginalia "
              "-- that is where layout analysis clips text. Re-run "
              "extract_text.py --force layout (or --force ocr) and compare.")
        return 1

    print(f"\nAll pages at or above {a.floor}. No layout-driven text loss.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
