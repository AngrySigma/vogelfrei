/* Vogelfrei – page enhancements
   1. Colour .md-tag chips by text content (fallback when tags plugin is off)
   2. Click-to-zoom lightbox for .vf-figure portraits

   The Class and Level lines of a spell/miracle metadata block used to be
   injected here from the page's tag chips. They are now written into the page
   itself by scripts/gen_game_data.py, which generates the block from the
   frontmatter that also feeds docs/data/*.json — so the rules text and the
   structured data cannot drift apart, and the lines are present in the HTML
   for search, for print, and for anything reading the page without JS.      */

const TAG_COLORS = {
  "magic-user": { bg: "var(--vf-tag-mu)", color: "var(--vf-tag-mu-text)" },
  "cleric":     { bg: "var(--vf-tag-cl)", color: "var(--vf-tag-cl-text)" },
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

/* ---- 2. Click-to-zoom lightbox for .vf-figure portraits (cover + careers) ----
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

/* ---- Run on load and on every instant-navigation page swap ----
   This file loads at the end of <body>, so the article is already parsed and
   we can enhance it before the first paint. document$ is Material's observable
   of the current document: it replays to late subscribers and emits again on
   every instant-navigation swap, which is what re-runs the enhancements after
   the theme swaps in new content. Both steps are idempotent (see the dataset
   guards above), so the double call on the initial load is harmless.

   Note: there is no "DOMContentSwitch" event — it is dispatched nowhere in the
   theme bundle. Listening for it silently does nothing, so anything that must
   re-run after an instant-navigation swap has to go through document$.     */
function run() {
  setupLightbox();
  colorTagChips();
}

run();
if (window.document$ && typeof window.document$.subscribe === "function") {
  window.document$.subscribe(run);
} else {
  document.addEventListener("DOMContentLoaded", run);
}
