/* Vogelfrei – spell page enhancements
   1. Colour .md-tag chips by text content (fallback when tags plugin is off)
   2. Inject Class + Level lines into the Duration/Range metadata block        */

const TAG_COLORS = {
  "magic-user": { bg: "var(--vf-tag-mu)", color: "var(--vf-tag-mu-text)" },
  "cleric":     { bg: "var(--vf-tag-cl)", color: "var(--vf-tag-cl-text)" },
};

const CLASS_LABELS = {
  "magic-user": "Magic-User",
  "cleric":     "Cleric",
};

/* ---- 1. Colour non-linked tag chips ---- */
function colorTagChips() {
  document.querySelectorAll(".md-tag:not([href])").forEach(chip => {
    const label = chip.textContent.trim().toLowerCase();
    const style = TAG_COLORS[label];
    if (style) {
      chip.style.background = style.bg;
      chip.style.color      = style.color;
    }
  });
}

/* ---- 2. Inject Class / Level into the metadata block ---- */
function injectSpellMeta() {
  /* Collect tag chip text (works for both <a> and <span> chips) */
  const chipTexts = [...document.querySelectorAll(".md-tag")]
    .map(el => el.textContent.trim().toLowerCase());

  const classTag = chipTexts.find(t => CLASS_LABELS[t]);
  const levelTag = chipTexts.find(t => /^level_\d+$/.test(t));

  if (!classTag && !levelTag) return; /* not a spell/miracle page */

  /* Find the metadata block: first <p> whose first element child is <strong>
     and which contains a <br> — the Duration/Range paragraph              */
  const metaBlock = [...document.querySelectorAll(".md-typeset p")].find(p => {
    const first = p.firstElementChild;
    return first && first.tagName === "STRONG" && p.querySelector("br");
  });

  if (!metaBlock) return;

  /* Avoid double-injection on instant-nav revisits */
  if (metaBlock.dataset.vfInjected) return;
  metaBlock.dataset.vfInjected = "1";

  /* Build lines to prepend */
  const lines = [];
  if (classTag) lines.push(["Class", CLASS_LABELS[classTag]]);
  if (levelTag) lines.push(["Level", levelTag.replace("level_", "")]);

  const frag = document.createDocumentFragment();
  lines.forEach(([label, value]) => {
    const strong = document.createElement("strong");
    strong.textContent = label;
    frag.appendChild(strong);
    frag.appendChild(document.createTextNode(": " + value));
    frag.appendChild(document.createElement("br"));
  });

  metaBlock.insertBefore(frag, metaBlock.firstChild);
}

/* ---- Run on load and on every instant-navigation page swap ---- */
function enhance() {
  colorTagChips();
  injectSpellMeta();
}

document.addEventListener("DOMContentLoaded", enhance);
document.addEventListener("DOMContentSwitch",  enhance); /* instant nav */
