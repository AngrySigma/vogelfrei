---
name: rpg-pdf-extract
description: Turn heavy illustrated PDFs -- RPG modules, rulebooks, art-heavy manuals, scanned books -- into compact Markdown plus the handful of page images that actually carry content, with a per-page check that no text was silently dropped. Use this whenever a PDF is too large to upload or attach, whenever someone wants a book's text without its art, whenever they ask to strip images from a PDF or shrink it, and whenever they want to pull maps, handouts, tables or stat blocks out of a book. Also use it before feeding any large illustrated PDF to another tool or model, since raw extraction quietly loses table cells and sidebars.
---

# Extracting illustrated books from PDF

A print-ready RPG module is 30-200 MB because its art is 300 dpi raster at full
page size. Its text is perhaps 400 KB. Almost every task involving one of these
files -- reading it, searching it, passing it to a model, getting it under an
upload cap -- is served by separating those two things rather than compressing
them together.

Two failure modes dominate, and both are silent:

- **Stripping art from a scan.** A scanned book's pages *are* images. Remove
  them and you have a valid PDF of blank pages. Always classify first.
- **Layout analysis dropping text.** Column detection decides where a table
  cell ends. When it decides wrong, the cell is truncated mid-word and the
  output still looks clean -- there is no error, no marker, just missing text.
  On a real two-column module this costs about 12 words per affected page,
  roughly 0.15% of the document, which is why aggregate quality checks miss it
  entirely.

The scripts here handle both. Run them in order.

## Setup

```bash
pip install pymupdf4llm          # pulls pymupdf and the layout engine
```

Optional: `poppler-utils` for `pdftotext`/`pdfimages` cross-checks,
`tesseract-ocr` for scanned books (the layout engine calls it automatically).

## Step 1 -- Classify before touching anything

```bash
python scripts/inspect_pdf.py BOOK.pdf
```

Reports size, page count, characters per page, embedded fonts, and a verdict:

- **DIGITAL** -- real text layer. Extract directly, never OCR.
- **SCAN** -- no text layer, pages are raster. Text extraction and image
  stripping both produce nothing. OCR is the only route.
- **SPARSE/VECTOR** -- little text, almost no raster images. The content is
  vector artwork with real text on top, so OCR would accomplish nothing and
  image stripping will not shrink the file. Extract text, render the figure
  pages at high dpi.
- **MIXED** -- some pages are scans or art-only plates. Extract, then OCR only
  the pages that came back empty.

It also lists image-dominated pages. Those are the map and handout candidates;
note the numbers, they feed steps 3 and 4.

## Step 2 -- Extract the text

```bash
python scripts/extract_text.py BOOK.pdf -o book.md
```

This tries three engines cheapest-first and stops at the first one whose
**worst page** clears a recall floor of 0.995:

| engine | speed | when it wins |
|---|---|---|
| legacy pymupdf4llm | ~25 pages/sec | simple single-column layouts |
| layout engine, no OCR | ~2 pages/sec | two-column text, tables, sidebars |
| layout engine + OCR | ~0.7 pages/sec | scans, and text baked into art |

The floor is deliberately tight. A clean born-digital page scores exactly
1.000, so 0.987 is not "almost perfect" -- it means roughly a dozen words
vanished from that page, which in practice is a truncated table row. Loosen it
only after looking at what was dropped.

Useful flags: `--pages 1-40` to work a chapter at a time on a big book,
`--force ocr` for a scan, `--floor` to adjust.

## Step 3 -- Verify, and look at what failed

```bash
python scripts/verify_extraction.py BOOK.pdf book.md
```

Scores every page against the raw glyph stream and names the pages that lost
text along with the specific words. Exit code 1 means something was dropped.

Open those pages in the PDF before trusting the output. The loss is almost
always a table cell, a sidebar, or marginalia clipped at a column boundary --
so if the page has a random table or a stat block, re-extract just that range
with `--force ocr` and splice it in, or transcribe the table by hand. A dozen
words from a d20 table is a dozen missing entries.

## Step 4 -- Pull out the figures that carry content

```bash
python scripts/extract_figures.py BOOK.pdf -o figures/
```

Most art is decorative: the text beside it says what it says. A few images are
load-bearing -- keyed maps, handouts, ciphers, diagrams -- and nothing in the
text layer records their content. This ranks pages by how much of the page a
single figure occupies, penalised by the prose sharing that page, and renders
the top candidates as PNGs.

Both raster and vector figures are ranked. That matters because a cartographer
exporting from Illustrator or Inkscape produces a map made of paths, not
pixels, which raster-only ranking is completely blind to. The discriminator is
span, not path count -- a five-room map covers 60% of its page while a table
grid covers 7%. Vector scanning costs about 3 ms/page; `--no-vector` disables
it. Vector maps rasterise cleanly, so push `--dpi 300` for those.

It renders the **whole page**, not the extracted image, so captions and keyed
numbers typeset beside the map come along. It will also surface chapter-opener
plates, which are noise -- glance at the output and delete those.

Use `--pages 14,15,88` to override the ranking when step 1 already told you
where the maps are.

## Step 5 -- Only if the output must stay a PDF

```bash
python scripts/slim_pdf.py BOOK.pdf -o slim.pdf --keep-auto
```

For a tablet copy to read at the table, or a tool that needs page structure.
`--keep-auto` preserves the pages step 4 would rank highest; `--keep 14,15,88`
names them explicitly.

If the destination only needs the content, skip this -- `book.md` is two orders
of magnitude smaller and carries no layout reconstruction risk.

## What to hand over

For review or analysis, the Markdown plus two or three figure PNGs beats the
original PDF on every axis: a 30 MB book becomes ~400 KB, reading order is
already resolved, and nothing has to re-derive column structure. Mention which
pages exist only as images so nobody assumes the text is complete.

## Things that bite

**Images nested in Form XObjects.** InDesign and reportlab wrap placed images
in forms, so a page-level strip misses the heaviest objects. `slim_pdf.py`
recurses; hand-rolled `pikepdf` loops usually do not.

**Dangling XObject references.** Deleting an image leaves the content stream's
`Do` operator pointing at a name that no longer exists. `qpdf --check` passes,
but poppler reports a syntax error on every affected page. `slim_pdf.py`
rewrites images to a 1x1 white pixel instead, which keeps every reference valid.

**`remove_unreferenced_resources()`.** Do not call it after mutating page
resources -- it deletes Form XObjects that content streams still reference and
corrupts the file. qpdf drops genuinely orphaned objects on write anyway.

**OCR cost.** Roughly 1.4 seconds per page, so a 200-page book is about five
minutes. Never let it run on a born-digital book: it adds nothing and inserts
garbage transcriptions of decorative art into the text stream.

**Extraction settings change table fidelity in both directions.** Options that
speed things up or clean up headers can also change how cells are segmented.
This is why step 3 exists as a separate check rather than a claim in this
document -- measure it on the actual book.

## Reference

`references/troubleshooting.md` covers encrypted files, books whose maps are
vector rather than raster, per-chapter splitting for very large volumes, and
what to do when recall is bad on every engine.
