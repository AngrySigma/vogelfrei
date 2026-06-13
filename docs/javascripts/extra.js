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

/* ---- 3. Click-to-zoom lightbox for .vf-figure portraits (cover + careers) ----
   Uses event delegation on document + a single reused overlay, so it works
   with instant navigation without re-binding on every page swap.            */
function setupLightbox() {
  if (document.body.dataset.vfLightbox) return; /* bind once */
  document.body.dataset.vfLightbox = "1";

  const overlay = document.createElement("div");
  overlay.className = "vf-lightbox";
  overlay.setAttribute("role", "dialog");
  overlay.setAttribute("aria-modal", "true");
  overlay.hidden = true;
  const big = document.createElement("img");
  overlay.appendChild(big);
  document.body.appendChild(overlay);

  function open(src, alt) {
    big.src = src;
    big.alt = alt || "";
    overlay.hidden = false;
    /* next frame so the opacity transition runs */
    requestAnimationFrame(() => overlay.setAttribute("data-open", ""));
  }
  function close() {
    overlay.removeAttribute("data-open");
    setTimeout(() => { overlay.hidden = true; big.src = ""; }, 200);
  }

  document.addEventListener("click", (e) => {
    const img = e.target.closest(".vf-figure img");
    if (img) { open(img.currentSrc || img.src, img.alt); return; }
    if (e.target === overlay || e.target === big) close();
  });
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && !overlay.hidden) close();
  });
}

/* ---- Run on load and on every instant-navigation page swap ---- */
function enhance() {
  colorTagChips();
  injectSpellMeta();
}

document.addEventListener("DOMContentLoaded", () => { setupLightbox(); enhance(); });
document.addEventListener("DOMContentSwitch", enhance); /* instant nav */
