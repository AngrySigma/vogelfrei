# Troubleshooting

Contents: encrypted files · vector maps · every engine scores badly · huge
books · stat blocks mangled · reading order wrong · output still too large

## The file is encrypted

`inspect_pdf.py` reports `encrypted: true` in its JSON. Most commercial RPG
PDFs carry an owner password that permits reading but restricts extraction.

```bash
qpdf --decrypt --password='' IN.pdf OUT.pdf      # empty owner password
```

If that fails the file needs a user password, which you must have legitimately;
do not attempt to recover one.

## The maps are vector, not raster

`extract_figures.py` ranks vector figures alongside raster ones, so these
normally surface on their own -- `inspect_pdf.py` will report a SPARSE/VECTOR
verdict and the ranker will label the page "vector art spans N%".

If a vector map still does not appear, it is probably inline within a text
column, where the word penalty suppresses it. Render by page number instead,
and push the resolution up, since vector art rasterises without artefacts:

```bash
python scripts/extract_figures.py BOOK.pdf -o figures/ --pages 22,23 --dpi 300
```

Vector content also means `slim_pdf.py` will barely shrink the file, because
the weight is in path data and embedded fonts rather than images. Extract the
text and forget the PDF.

## Every engine scores below the floor

Look at *which* pages fail before assuming the tooling is at fault.

- **A handful of pages, all with tables** -- expected. Accept the best engine
  and repair those tables by hand or with a targeted `--force ocr` run over
  just that range.
- **Every page, by a similar margin** -- usually a header or footer the
  reference counts and the extractor deliberately drops. Harmless. Confirm by
  checking whether the missing words are the running head, then lower `--floor`.
- **Every page, badly (below 0.9)** -- suspect a broken or synthetic text
  layer, common in books OCRed once and saved with a bad layer. Compare
  `pdftotext -raw` output against what the page visibly says. If the existing
  layer is garbage, discard it and re-OCR:

```bash
ocrmypdf --force-ocr --output-type pdf IN.pdf OUT.pdf
```

## The book is very large

Work in chapters. Memory use and OCR time both scale with page count, and a
failure 180 pages in costs the whole run.

```bash
for r in 1-60 61-120 121-180 181-240; do
  python scripts/extract_text.py BOOK.pdf -o "part-$r.md" --pages "$r"
done
cat part-*.md > book.md
```

Bookmarks give natural split points when present -- `inspect_pdf.py --json`
reports whether the file has a TOC.

## Stat blocks come out as code fences or garbled

Monospace fonts trigger code-block detection. That is usually fine and even
useful, since it preserves the line breaks that make a stat block readable. If
it is unwanted, re-run with the legacy engine and `ignore_code=True`, or strip
the fences afterwards.

Stat blocks set in a narrow sidebar are a different problem: they are prone to
exactly the column-boundary clipping step 3 detects. Check them specifically --
a dropped `hp` or damage die is easy to miss and expensive at the table.

## Reading order is scrambled

The recall check measures *loss*, not *order*, so a page can score 1.000 and
still interleave two columns. Symptoms: sentences that break off and resume
several paragraphs later.

The layout engine handles columns well; the legacy engine is weaker. If
`extract_text.py` settled on the fast path because recall was fine, force the
better one:

```bash
python scripts/extract_text.py BOOK.pdf -o book.md --force layout
```

For a quick visual check of whether the source is even two-column, compare
`pdftotext -layout` (preserves visual position, wrong reading order) against
the Markdown.

## The slimmed PDF is still too large

Then raster art was not the weight. Check what is:

```bash
python -c "
import pymupdf, collections
d = pymupdf.open('BOOK.pdf')
print('fonts:', len({f[3] for i in range(d.page_count) for f in d.get_page_fonts(i)}))
print('pages with vector drawings:', sum(1 for p in d if len(p.get_drawings()) > 50))
"
```

Many embedded fonts or heavy vector drawings both resist image stripping. At
that point the options are splitting the file by chapter, or giving up on the
PDF form and shipping the Markdown plus figure renders.
