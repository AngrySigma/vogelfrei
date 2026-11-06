#!/usr/bin/env python3
"""Triage a PDF before extracting anything.

The single decision that governs everything downstream is whether the file has
a real text layer. Image-stripping a scan leaves blank pages; running OCR on a
born-digital book wastes minutes per hundred pages. This prints the evidence
for that decision plus a per-page inventory, and exits with a recommendation.

Usage: python inspect_pdf.py BOOK.pdf [--json OUT.json]
"""
import argparse
import json
import os
import sys

import pymupdf


def analyse(path):
    doc = pymupdf.open(path)
    pages = []
    for i, page in enumerate(doc):
        text = page.get_text("text").strip()
        imgs = page.get_images(full=True)
        parea = abs(page.rect.width * page.rect.height) or 1.0
        img_area = 0.0
        for im in page.get_image_info():
            b = im.get("bbox")
            if b:
                img_area += abs((b[2] - b[0]) * (b[3] - b[1]))
        pages.append({
            "page": i + 1,
            "chars": len(text),
            "words": len(text.split()),
            "images": len(imgs),
            "image_coverage": round(min(img_area / parea, 1.0), 3),
        })
    total_chars = sum(p["chars"] for p in pages)
    textish = sum(1 for p in pages if p["words"] > 40)
    fonts = set()
    embedded = 0
    for i in range(doc.page_count):
        for f in doc.get_page_fonts(i):
            fonts.add(f[3])
            if f[1] not in ("n/a", ""):
                embedded += 1
    info = {
        "path": os.path.abspath(path),
        "size_mb": round(os.path.getsize(path) / 1e6, 1),
        "pages": doc.page_count,
        "encrypted": doc.is_encrypted,
        "total_chars": total_chars,
        "chars_per_page": round(total_chars / max(doc.page_count, 1)),
        "text_pages": textish,
        "fonts": sorted(fonts),
        "has_toc": bool(doc.get_toc()),
        "page_detail": pages,
    }
    # A born-digital book carries hundreds of characters per page. A scan
    # carries a handful -- but so does a page of vector diagrams, and the two
    # need opposite treatment. What separates them is what the sparse pages
    # are made of: a scan is raster with no real fonts, a vector page has
    # fonts and drawings and no images at all. OCRing the latter accomplishes
    # nothing, since its text is already text.
    img_pages = sum(1 for p in pages if p["images"])
    if info["chars_per_page"] > 400 and textish >= 0.5 * doc.page_count:
        info["verdict"] = "digital"
        info["recommendation"] = "Extract text directly. Do not OCR."
    elif total_chars < 100 and img_pages >= 0.5 * doc.page_count:
        info["verdict"] = "scan"
        info["recommendation"] = (
            "No text layer, pages are raster. OCR is required; text "
            "extraction and image stripping will both produce empty output.")
    elif total_chars < 100 and not fonts:
        info["verdict"] = "scan"
        info["recommendation"] = (
            "No text layer and no embedded fonts. OCR is required.")
    elif info["chars_per_page"] < 400 and img_pages < 0.3 * doc.page_count:
        info["verdict"] = "sparse/vector"
        info["recommendation"] = (
            "Little text and almost no raster images -- content is likely "
            "vector artwork (maps, diagrams) with real text on top. Do NOT "
            "OCR. Extract the text, then render figure pages with "
            "extract_figures.py --dpi 300; image stripping will not shrink "
            "this file.")
    else:
        info["verdict"] = "mixed"
        info["recommendation"] = (
            "Partial text layer -- some pages are scans or art-only. Extract "
            "text, then check which pages came back empty and OCR only those.")
    doc.close()
    return info


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pdf")
    ap.add_argument("--json", dest="json_out")
    a = ap.parse_args()
    info = analyse(a.pdf)

    print(f"{os.path.basename(info['path'])}: {info['size_mb']} MB, "
          f"{info['pages']} pages, {info['chars_per_page']} chars/page")
    print(f"fonts: {', '.join(info['fonts'][:6]) or 'NONE'}"
          f"{' ...' if len(info['fonts']) > 6 else ''}")
    print(f"bookmarks/TOC: {'yes' if info['has_toc'] else 'no'}")
    print(f"VERDICT: {info['verdict'].upper()} -- {info['recommendation']}")

    heavy = [p for p in info["page_detail"] if p["image_coverage"] > 0.45]
    if heavy:
        print(f"\n{len(heavy)} image-dominated pages (candidate maps/handouts/"
              f"full-page art):")
        for p in heavy[:25]:
            print(f"  p{p['page']:>4}  coverage {p['image_coverage']:.0%}  "
                  f"{p['words']:>5} words")
        if len(heavy) > 25:
            print(f"  ... {len(heavy) - 25} more")

    thin = [p for p in info["page_detail"] if p["words"] < 15 and p["images"]]
    if thin:
        print(f"\n{len(thin)} pages with art but almost no text "
              f"(pure plates, or scanned pages if verdict is scan/mixed): "
              f"{', '.join(str(p['page']) for p in thin[:20])}"
              f"{' ...' if len(thin) > 20 else ''}")

    if a.json_out:
        with open(a.json_out, "w") as fh:
            json.dump(info, fh, indent=2)
        print(f"\nwrote {a.json_out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
