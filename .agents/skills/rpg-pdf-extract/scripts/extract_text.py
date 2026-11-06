#!/usr/bin/env python3
"""Extract a book's text to Markdown, escalating engines until recall is good.

Why escalation rather than one fixed call: extractor settings silently drop
text. On a two-column page with a table, the fast path truncates cells at the
column boundary ("...went down th") and you only notice by reading the output.
So every candidate is scored against `pdftotext -raw`, which has no layout
model and therefore no layout-driven truncation -- it is a poor reading order
but a near-complete bag of words. Word recall against that bag is a cheap,
deterministic proxy for "did we lose content", and the cheapest candidate that
clears the threshold wins.

Usage:
  python extract_text.py BOOK.pdf -o out.md [--min-recall 0.98] [--pages 1-40]
"""
import argparse
import os
import re
import sys
import time
from collections import Counter

import pymupdf
import pymupdf4llm

WORD = re.compile(r"[0-9a-z']+")


def bag(text):
    return Counter(WORD.findall(text.lower()))


def page_references(pdf, pages=None):
    """Per-page word bags straight from the glyph stream, with no column
    detection or table reconstruction applied. Whatever a candidate is missing
    relative to this was discarded by layout analysis."""
    doc = pymupdf.open(pdf)
    refs = []
    for i, page in enumerate(doc):
        if pages is not None and i not in pages:
            continue
        b = bag(page.get_text("text"))
        if sum(b.values()) >= 25:      # skip art plates and title pages
            refs.append((i + 1, b))
    doc.close()
    return refs


def score(md, refs):
    """Return (worst-page recall, that page number, the words it dropped).

    The floor matters, not the mean. Clipped table cells cost ~12 words out of
    8,000 document-wide -- 99.85%, invisible -- but ~12 out of 760 on their own
    page, which is 98.4% and stands out against the 100.0% every clean page
    scores."""
    if not refs:
        return None, None, []
    cand = bag(md)
    worst = (2.0, None, [])
    for pno, ref in refs:
        total = sum(ref.values())
        lost, missing = 0, []
        for w, n in ref.items():
            gap = n - cand.get(w, 0)
            if gap > 0:
                lost += gap
                missing.append((gap, w))
        r = 1.0 - lost / total
        if r < worst[0]:
            missing.sort(reverse=True)
            worst = (r, pno, [w for _, w in missing[:10]])
    return worst


def parse_pages(spec, count):
    if not spec:
        return None
    out = []
    for part in spec.split(","):
        if "-" in part:
            a, b = part.split("-")
            out.extend(range(int(a) - 1, int(b)))
        else:
            out.append(int(part) - 1)
    return [p for p in out if 0 <= p < count]


def candidates():
    """Ordered cheapest-first. Each entry: (name, use_layout, kwargs)."""
    return [
        ("fast (legacy engine)", False,
         dict(ignore_images=True, table_strategy="lines_strict")),
        ("layout engine, no OCR", True,
         dict(use_ocr=False, header=False, footer=False, page_separators=True)),
        ("layout engine + OCR", True,
         dict(use_ocr=True, header=False, footer=False, page_separators=True)),
    ]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pdf")
    ap.add_argument("-o", "--out", required=True)
    ap.add_argument("--pages", help="e.g. 1-40 or 3,7,9-12 (1-based)")
    ap.add_argument("--floor", type=float, default=0.995,
                    help="minimum per-page recall to accept an engine; a clean "
                         "born-digital extraction scores 1.000, so the margin "
                         "here is small on purpose")
    ap.add_argument("--force", choices=["fast", "layout", "ocr"],
                    help="skip escalation and use one engine")
    a = ap.parse_args()

    doc = pymupdf.open(a.pdf)
    pages = parse_pages(a.pages, doc.page_count)
    doc.close()

    refs = page_references(a.pdf, pages)
    if not refs:
        print("! no text layer to score against -- this looks like a scan. "
              "Run with --force ocr, or OCR the file first.")

    picks = candidates()
    if a.force:
        picks = [picks[{"fast": 0, "layout": 1, "ocr": 2}[a.force]]]

    best = None
    for name, use_layout, kw in picks:
        pymupdf4llm.use_layout(use_layout)
        t0 = time.time()
        try:
            md = pymupdf4llm.to_markdown(a.pdf, pages=pages, **kw)
        except Exception as exc:                      # engine-specific breakage
            print(f"  {name}: failed ({exc})")
            continue
        secs = time.time() - t0
        r, pno, missing = score(md, refs)
        shown = "n/a" if r is None else f"{r:.3f} (worst page p{pno})"
        print(f"  {name}: {len(md):>7} chars, {secs:6.1f}s, floor {shown}")
        if best is None or (r or 0) > (best[1] or 0):
            best = (md, r, name, pno, missing)
        if r is None or r >= a.floor:
            break

    md, r, name, pno, missing = best
    with open(a.out, "w") as fh:
        fh.write(md)

    print(f"\nengine: {name}")
    print(f"wrote {a.out} ({len(md)/1000:.0f}k chars, "
          f"{os.path.getsize(a.out)/1e6:.2f} MB)")
    if r is not None and r < a.floor:
        print(f"! p{pno} recall {r:.3f} is below {a.floor}; it dropped: "
              f"{', '.join(missing)}")
        print("! Look at that page in the PDF. Loss this shape is almost "
              "always a table cell or sidebar clipped at a column boundary, "
              "so check any table on it before relying on the text.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
