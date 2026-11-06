#!/usr/bin/env python3
"""Export the images that carry content, and skip the ones that carry mood.

In an illustrated module most raster images are decoration: the text beside
them says everything they say. A few are load-bearing -- keyed dungeon maps,
player handouts, cipher plates, diagrams -- and their content exists nowhere in
the text layer. Strip those and the extraction is missing the dungeon.

The separating signal is that a load-bearing figure occupies most of its page
and is surrounded by little prose, because the layout gives it room. Decorative
art sits inside a text column. So rank by page coverage with a penalty for the
word count sharing the page, then render whole pages (not the raw image) for
the top candidates, which keeps the caption and any keyed numbers typeset
beside the figure.

Usage: python extract_figures.py BOOK.pdf -o figures/ [--max 12] [--dpi 150]
       python extract_figures.py BOOK.pdf -o figures/ --pages 14,15,88
"""
import argparse
import os
import sys

import pymupdf


def page_scores(doc, vector=True):
    rows = []
    for i, page in enumerate(doc):
        area = abs(page.rect.width * page.rect.height) or 1.0
        cov = 0.0
        biggest = 0.0
        for im in page.get_image_info():
            b = im.get("bbox")
            if not b:
                continue
            a = abs((b[2] - b[0]) * (b[3] - b[1])) / area
            cov += a
            biggest = max(biggest, a)
        cov = min(cov, 1.0)

        # A map drawn as vector paths has no image at all, so raster coverage
        # alone is blind to it -- and vector maps are common, since that is
        # what a cartographer's export looks like. The signature is not path
        # count: a map and a table grid both run about a dozen paths. It is
        # how far they span. A five-room map covers 60%+ of its page; a table
        # grid on a prose page covers 7%, and the word penalty below buries
        # it regardless. The floor of six paths exists only to exclude single
        # decorative page borders.
        vec = 0.0
        if vector:
            try:
                draws = page.get_drawings()
            except Exception:
                draws = []
            if len(draws) >= 6:
                xs0 = min(d["rect"].x0 for d in draws)
                ys0 = min(d["rect"].y0 for d in draws)
                xs1 = max(d["rect"].x1 for d in draws)
                ys1 = max(d["rect"].y1 for d in draws)
                vec = min(abs((xs1 - xs0) * (ys1 - ys0)) / area, 1.0)

        words = len(page.get_text("text").split())
        figure = max(biggest, vec)
        # Coverage drives the score; prose on the same page argues the figure
        # is illustrating text that already exists in the extraction.
        score = figure - min(words / 400.0, 0.8)
        rows.append({"page": i + 1, "coverage": cov, "biggest": biggest,
                     "vector": vec, "figure": figure, "words": words,
                     "score": score})
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pdf")
    ap.add_argument("-o", "--out", required=True)
    ap.add_argument("--dpi", type=int, default=150)
    ap.add_argument("--max", type=int, default=12)
    ap.add_argument("--min-coverage", type=float, default=0.35)
    ap.add_argument("--pages", help="explicit 1-based page list, skips ranking")
    ap.add_argument("--no-vector", action="store_true",
                    help="rank raster images only; vector scanning costs a "
                         "path walk per page on very large books")
    a = ap.parse_args()

    os.makedirs(a.out, exist_ok=True)
    doc = pymupdf.open(a.pdf)

    if a.pages:
        chosen = [{"page": int(p), "coverage": None, "vector": None, "score": None}
                  for p in a.pages.replace(" ", "").split(",")]
    else:
        rows = [r for r in page_scores(doc, vector=not a.no_vector)
                if r["figure"] >= a.min_coverage]
        rows.sort(key=lambda r: r["score"], reverse=True)
        chosen = rows[:a.max]
        chosen.sort(key=lambda r: r["page"])

    if not chosen:
        print("No page-dominating figures found. The maps may sit inline "
              "within text columns -- try lowering --min-coverage.")
        return 0

    zoom = a.dpi / 72.0
    written = []
    for r in chosen:
        page = doc[r["page"] - 1]
        pix = page.get_pixmap(matrix=pymupdf.Matrix(zoom, zoom))
        name = os.path.join(a.out, f"p{r['page']:04d}.png")
        pix.save(name)
        written.append((name, r))

    print(f"wrote {len(written)} page renders to {a.out}/ at {a.dpi} dpi")
    for name, r in written:
        if r["coverage"] is None:
            cov = ""
        elif r.get("vector", 0) > r["coverage"]:
            cov = f"  vector art spans {r['vector']:.0%}"
        else:
            cov = f"  image covers {r['coverage']:.0%}"
        mb = os.path.getsize(name) / 1e6
        print(f"  {os.path.basename(name)}  {mb:.2f} MB{cov}")
    print("\nCheck these before deleting the source: the ranking finds "
          "page-dominating art, which catches maps and handouts but also "
          "catches chapter-opener plates.")
    doc.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
