#!/usr/bin/env python3
"""Produce a lightweight PDF by removing raster art, keeping chosen pages whole.

Use this when the output has to stay a PDF -- something to read on a tablet at
the table, or to hand to a tool that wants page structure. If the destination
just needs the content, extract_text.py gives a file two orders of magnitude
smaller and skips layout reconstruction entirely.

Removal is by image XObject reference, and the same reference is usually shared
by every page that shows it (a repeated border, a chapter ornament), so one
deletion can shrink many pages. Pages named with --keep are left untouched,
which is how map and handout pages survive.

Usage:
  python slim_pdf.py BOOK.pdf -o slim.pdf --keep 14,15,88
  python slim_pdf.py BOOK.pdf -o slim.pdf --keep-auto      # keep ranked figures
"""
import argparse
import os
import sys

import pikepdf


def auto_keep(path, min_coverage=0.35, limit=12):
    """Same ranking as extract_figures.py, so the two agree on what matters."""
    try:
        import pymupdf
    except ImportError:
        return []
    doc = pymupdf.open(path)
    rows = []
    for i, page in enumerate(doc):
        area = abs(page.rect.width * page.rect.height) or 1.0
        biggest = 0.0
        for im in page.get_image_info():
            b = im.get("bbox")
            if b:
                biggest = max(biggest,
                              abs((b[2] - b[0]) * (b[3] - b[1])) / area)
        if biggest >= min_coverage:
            words = len(page.get_text("text").split())
            rows.append((biggest - min(words / 400.0, 0.8), i + 1))
    doc.close()
    rows.sort(reverse=True)
    return sorted(p for _, p in rows[:limit])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pdf")
    ap.add_argument("-o", "--out", required=True)
    ap.add_argument("--keep", default="", help="1-based pages to leave intact")
    ap.add_argument("--keep-auto", action="store_true",
                    help="keep the pages extract_figures.py would rank highest")
    a = ap.parse_args()

    keep = {int(p) for p in a.keep.replace(" ", "").split(",") if p}
    if a.keep_auto:
        found = auto_keep(a.pdf)
        keep |= set(found)
        print(f"auto-keeping pages: {', '.join(map(str, found)) or 'none found'}")

    before = os.path.getsize(a.pdf)
    pdf = pikepdf.open(a.pdf)
    removed = 0
    touched = 0

    def blank(img):
        """Shrink an image to a single white pixel, in place.

        Deleting the object instead would leave the content stream's `/Name Do`
        operator pointing at nothing. Readers mostly skip a dangling reference,
        but not all of them quietly -- poppler reports a syntax error on every
        page. Rewriting the object keeps every reference valid while dropping
        the payload; the placement matrix stretches one white pixel over the
        space the art occupied, so the page keeps its layout and gets a gap."""
        for key in ("/SMask", "/Mask", "/DecodeParms", "/Decode",
                    "/Interpolate", "/ColorTransform"):
            if key in img:
                del img[key]
        img.write(b"\xff")
        img["/Width"] = 1
        img["/Height"] = 1
        img["/ColorSpace"] = pikepdf.Name("/DeviceGray")
        img["/BitsPerComponent"] = 8

    def strip(res, seen):
        """Delete image XObjects, descending through Form XObjects.

        Layout tools routinely wrap a placed image in a form -- reportlab and
        InDesign both do -- so a page-level pass alone leaves the heaviest
        objects in place. Forms themselves must survive: they are referenced by
        name from the content stream, and removing one leaves a dangling
        reference that breaks every reader."""
        n = 0
        if res is None or "/XObject" not in res:
            return 0
        xo = res["/XObject"]
        for k in list(xo.keys()):
            obj = xo[k]
            sub = obj.get("/Subtype")
            if sub == pikepdf.Name("/Image"):
                blank(obj)
                n += 1
            elif sub == pikepdf.Name("/Form"):
                key = obj.objgen
                if key in seen:
                    continue
                seen.add(key)
                n += strip(obj.get("/Resources"), seen)
        return n

    seen = set()
    for i, page in enumerate(pdf.pages, start=1):
        if i in keep:
            continue
        n = strip(page.get("/Resources"), seen)
        removed += n
        touched += 1 if n else 0

    # No remove_unreferenced_resources() here: it walks page resources without
    # fully resolving names used inside content streams, and after this kind of
    # mutation it will happily delete forms the streams still call. qpdf drops
    # genuinely orphaned image objects on write anyway.
    pdf.save(a.out, linearize=True,
             object_stream_mode=pikepdf.ObjectStreamMode.generate,
             compress_streams=True)
    pdf.close()

    after = os.path.getsize(a.out)
    print(f"blanked {removed} image(s) across {touched} pages; "
          f"{len(keep)} page(s) kept intact")
    print(f"{before/1e6:.1f} MB -> {after/1e6:.1f} MB "
          f"({100 * (1 - after / before):.0f}% smaller)")
    if after > 30e6:
        print("! Still above 30 MB. Vector-heavy pages or embedded fonts "
              "dominate, not raster art -- extract the text instead, or split "
              "the file by chapter.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
