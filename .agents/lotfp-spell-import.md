# Importing spells from LotFP Rules & Magic

The Magic-User and Cleric spell lists come from *LotFP Weird Fantasy Role-Playing — Player Core Book: Rules & Magic* (2013). The author keeps the PDF at `~/lotfp/lotfp.pdf`, outside the repo. Its text is Open Game Content. The only Product Identity is the art, the layout and the LotFP / Lamentations names, so those names appear in `LICENSE` §15 and nowhere else in the book. Import one spell level per request; the `Level N` folders show which levels exist.

## Steps

1. **Extract** with PyMuPDF. The machine has no poppler or pypdf, so run it as `uv run --no-project --with pymupdf python -I script.py ~/lotfp/lotfp.pdf out.txt`. The pages have two columns, and `get_text("text", sort=True)` interleaves them. Use `page.get_text("blocks")` instead, keep the text blocks (`b[6] == 0`), sort them by column (`x0 < page.rect.width/2`) and then by `y0`, and write a blank line after each block. One block is one paragraph.
2. **Slice entries.** An entry is a name line followed by `Magic-User Level N` or `Cleric Level N`, then `Duration:` and `Range:`, then the paragraphs. Match the heading case-insensitively with `(Magic-User|Cleric)( Level)? \d`: Weird Vortex and Phase Door are printed as `Magic-User N`, and Mind Switch as `Magic-user Level 6`; a stricter pattern swallows each into the spell before it. Lost Dweomer (Magic-User 9) is on the list but has no description in the book. Tables come out as loose cells — render the page (`page.get_pixmap(dpi=110).save(...)`) and read the image to rebuild them. The spell lists are on PDF pages 90–91 (printed pages 86–87). The descriptions are alphabetical, with both classes mixed together.
3. **Clean.**
   - Drop the page-number lines and the running headers `Rules & Magic` and `Spell Descriptions`. One header gets fused to its page number, as in `114 Rules & Magic`.
   - A column or page break splits a paragraph into two blocks. Rejoin any block that doesn't end in terminal punctuation onto the one before it.
   - Rejoin words broken at the end of a line with a soft hyphen (U+00AD).
   - Turn thin spaces (U+2009) in ranges into plain spaces.
   - Write `mêlée` as `melee`.
4. **Adapt.** Keep the book's wording and change only these:
   - `*` in the list marks a reversible spell. Bold the reverse's name where the text introduces it, as in `**Continual Darkness**, the reverse of the spell, …`.
   - Give inverted names natural word order (`Light, Continual` becomes `Continual Light`).
   - Link spell names to pages that exist. Leave a name as plain text when its page doesn't exist yet.
   - Rebalancing is the author's job. Report anything that looks off, such as Web's escape times, and leave the numbers as printed.
   - Spell names keep the book's Evil/Good (Detect Evil, Protection from Evil, Dispel Evil), and so does the book's note that "Evil" is colloquial. The effect text uses Order/Chaos: Lawful → Orderly, Law → Order.
   - Game terms. Ability scores: Wisdom → Willpower, Charisma → Leadership, Dexterity → Agility, Constitution → Toughness (Strength and Intelligence stay). Hit Points → Wounds. Classes: Fighter → Warrior, Specialist → Rogue. Drop every mention of Elves, Dwarfs, Halflings or demihumans. Drop Initiative Segments; Vogelfrei uses side initiative.
   - Saves are Paralysation, Poison, Breath Weapon, Magical Device and Magic. "Save or die" is versus Poison.
5. **Write pages** to `docs/Character/Classes/<Class>/Spells|Miracles/Level N/<Name>.md` in the format in [page-contracts.md](page-contracts.md). Tier follows character level: a spell castable by a level 1–3 character is Base (no tier key), anything else is `tier: expert`. With the current slot grids (Wizard and Priest careers), that is Magic-User spell levels 1–2 and Cleric level 1 in Base.
6. **Wire them up**:
   - Append a `### Level N` section to the class's list page (`Spells/index.md` or `Miracles/index.md`).
   - Add a `{ "Level N" = [...] }` nav group after the previous level in `zensical.toml`.
   - Run `gen_game_data.py`, `gen_view_manifest.py` and `gen_llms_txt.py`. `gen_llms_txt.py` imports `tomllib`, so it needs Python 3.11 or newer: `uv run --no-project --python 3.12 python scripts/gen_llms_txt.py`.
   - Run `uv run zensical build`.

   The import is complete when `docs/data/spells.json` has a row for every spell on that level's list and `llms.txt` lists no Unlisted pages.
