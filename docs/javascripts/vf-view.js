/* =====================================================================
   Vogelfrei – game tier switcher
   =====================================================================
   Reads window.VF_TIERS / window.VF_PAGES (emitted by
   scripts/gen_view_manifest.py) and prunes the navigation client-side so
   each tier shows only the pages that belong to it.

   Tier membership is an explicit SET, not a cumulative rank: a page listed
   as [simple] appears in the Simple view and nowhere else. That is what
   lets "Basic Retainers" exist only in Simple while Base/Advanced replace
   it with the three detailed Retainers pages.

   Pages with no manifest entry are visible in every tier. Gating is purely
   cosmetic — hidden pages are still built, still linked, still indexed by
   search, and still reachable by direct URL. Landing on one shows a banner
   offering to switch to a tier that includes it.

   State lives in localStorage, so it is per-reader and survives navigation.
   ===================================================================== */

const VF_STORAGE_KEY = "vf-view";
const VF_DEFAULT_TIER = "base";

function vfTiers() {
  return window.VF_TIERS || ["simple", "base", "advanced"];
}

function vfTierLabel(tier) {
  return tier.charAt(0).toUpperCase() + tier.slice(1);
}

function vfGetView() {
  try {
    const raw = JSON.parse(localStorage.getItem(VF_STORAGE_KEY) || "{}");
    if (vfTiers().indexOf(raw.tier) !== -1) return { tier: raw.tier };
  } catch (e) {
    /* corrupt or unavailable storage — fall through to the default */
  }
  return { tier: VF_DEFAULT_TIER };
}

function vfSetView(view) {
  try {
    localStorage.setItem(VF_STORAGE_KEY, JSON.stringify({ tier: view.tier }));
  } catch (e) {
    /* private mode / quota — the view still applies for this page load */
  }
}

/* ---- Manifest lookup ------------------------------------------------
   Manifest keys are relative URL paths with a trailing slash and no leading
   slash (e.g. "Retainers/Basic Retainers/"). Match a link or page pathname
   by longest suffix, so a deploy base path — GitHub Pages serves this under
   "/vogelfrei/" — doesn't break lookups. Keys are stored un-encoded, so the
   pathname is decoded before comparing.                                  */

let VF_SORTED_KEYS = null;
function vfSortedKeys() {
  if (!VF_SORTED_KEYS) {
    VF_SORTED_KEYS = Object.keys(window.VF_PAGES || {})
      .filter(Boolean)
      .sort((a, b) => b.length - a.length);
  }
  return VF_SORTED_KEYS;
}

function vfPathOf(href) {
  try {
    return decodeURIComponent(new URL(href, document.baseURI).pathname);
  } catch (e) {
    return null; /* malformed href or stray '%' in the path */
  }
}

function vfMetaFor(pathname) {
  if (!pathname) return null;
  for (const key of vfSortedKeys()) {
    if (pathname.endsWith("/" + key)) return window.VF_PAGES[key];
  }
  return null;
}

function vfIsVisible(meta, view) {
  if (!meta || !meta.tiers) return true; /* untagged pages live in every tier */
  return meta.tiers.indexOf(view.tier) !== -1;
}

/* ---- Navigation pruning --------------------------------------------- */
function vfPruneNav(view) {
  /* Scope to the primary sidebar. The secondary nav is the current page's
     table of contents, whose links are bare "#anchor" hrefs that resolve to
     the current pathname — pruning those would hide the whole ToC whenever
     the reader is on a gated page. */
  const root = document.querySelector(".md-nav--primary");
  if (!root) return;

  /* Items whose visibility the manifest decided outright. With
     navigation.indexes a section's own index page is a link inside the
     section's item, so gating an index page gates the whole section — that
     verdict must survive the empty-section pass below. */
  const decided = new Set();

  root.querySelectorAll(".md-nav__link[href]").forEach(a => {
    const href = a.getAttribute("href");
    if (!href || href.charAt(0) === "#") return;
    const item = a.closest(".md-nav__item");
    if (!item) return;
    const meta = vfMetaFor(vfPathOf(a.href));
    /* Only touch pages the manifest knows about, so untagged items keep
       whatever the theme gave them. Both branches are assigned, so switching
       tiers restores what a previous tier hid. */
    if (!meta) return;
    item.style.display = vfIsVisible(meta, view) ? "" : "none";
    decided.add(item);
  });

  /* Collapse sections left with nothing in them. Reverse document order puts
     inner sections before the outer sections that contain them, so an outer
     section sees its children's resolved state. */
  const sections = [...root.querySelectorAll(".md-nav__item--nested")].reverse();
  sections.forEach(section => {
    if (decided.has(section)) return;
    const alive = [...section.querySelectorAll(".md-nav__item")]
      .some(item => item.style.display !== "none");
    section.style.display = alive ? "" : "none";
  });
}

/* ---- Banner shown when a hidden page is opened directly -------------- */
function vfRenderBanner(view) {
  const existing = document.getElementById("vf-view-banner");
  const container = document.querySelector(".md-content__inner");
  const meta = vfMetaFor(vfPathOf(location.href));
  const hidden = meta && !vfIsVisible(meta, view);

  if (!hidden || !container) {
    if (existing) existing.remove();
    return;
  }
  /* Already showing, and its text depends only on the page's own tiers —
     leave the node alone. Re-creating it on every apply would churn the DOM
     and destroy the buttons mid-interaction. */
  if (existing) return;

  const tiers = meta.tiers.map(vfTierLabel).join(" / ");
  const banner = document.createElement("div");
  banner.id = "vf-view-banner";
  banner.className = "vf-view-banner";

  const text = document.createElement("p");
  text.append("This page belongs to the ");
  const strong = document.createElement("strong");
  strong.textContent = tiers;
  text.append(strong, " view. It is hidden from navigation in your current view.");
  banner.appendChild(text);

  const reveal = document.createElement("button");
  reveal.type = "button";
  reveal.className = "vf-view-banner__btn";
  reveal.textContent = "Switch to " + vfTierLabel(meta.tiers[0]);
  reveal.addEventListener("click", () => {
    const next = { tier: meta.tiers[0] };
    vfSetView(next);
    vfApplyView();
    vfSyncControl(next);
  });

  const dismiss = document.createElement("button");
  dismiss.type = "button";
  dismiss.className = "vf-view-banner__btn vf-view-banner__btn--ghost";
  dismiss.textContent = "Dismiss";
  dismiss.addEventListener("click", () => banner.remove());

  banner.append(reveal, dismiss);
  container.insertBefore(banner, container.firstChild);
}

/* ---- Header control -------------------------------------------------- */
function vfEnsureControl() {
  if (document.getElementById("vf-view-control")) return;
  const header = document.querySelector(".md-header__inner");
  if (!header) return;

  const view = vfGetView();

  const wrap = document.createElement("div");
  wrap.id = "vf-view-control";
  wrap.className = "vf-view-control";

  const toggle = document.createElement("button");
  toggle.type = "button";
  toggle.className = "md-header__button md-icon vf-view-control__toggle";
  toggle.setAttribute("aria-label", "Game view");
  toggle.setAttribute("aria-expanded", "false");
  toggle.title = "Game view";
  toggle.innerHTML =
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" ' +
    'height="24" fill="currentColor"><path d="M12 4.5C7 4.5 2.7 7.6 1 12c1.7 ' +
    '4.4 6 7.5 11 7.5s9.3-3.1 11-7.5c-1.7-4.4-6-7.5-11-7.5zm0 12.5a5 5 0 ' +
    '110-10 5 5 0 010 10zm0-8a3 3 0 100 6 3 3 0 000-6z"/></svg>';

  const panel = document.createElement("div");
  panel.className = "vf-view-panel";
  panel.hidden = true;

  const group = document.createElement("fieldset");
  group.className = "vf-view-panel__group";
  const legend = document.createElement("legend");
  legend.textContent = "Game view";
  group.appendChild(legend);

  vfTiers().forEach(tier => {
    const label = document.createElement("label");
    label.className = "vf-view-panel__opt";
    const input = document.createElement("input");
    input.type = "radio";
    input.name = "vf-tier";
    input.value = tier;
    input.checked = view.tier === tier;
    const span = document.createElement("span");
    span.textContent = vfTierLabel(tier);
    label.append(input, span);
    group.appendChild(label);
  });
  panel.appendChild(group);

  panel.addEventListener("change", () => {
    const selected = panel.querySelector('input[name="vf-tier"]:checked');
    if (!selected) return;
    vfSetView({ tier: selected.value });
    vfApplyView();
  });

  toggle.addEventListener("click", e => {
    e.stopPropagation();
    panel.hidden = !panel.hidden;
    toggle.setAttribute("aria-expanded", String(!panel.hidden));
  });

  wrap.append(toggle, panel);

  const anchor = header.querySelector(".md-header__option, .md-header__source");
  if (anchor) header.insertBefore(wrap, anchor);
  else header.appendChild(wrap);
}

/* Close the panel on an outside click or Escape. Bound once on document, not
   per control — instant navigation can rebuild the header, and re-binding
   there would leak a listener holding a dead node on every page swap. */
function vfClosePanel() {
  const wrap = document.getElementById("vf-view-control");
  const panel = wrap && wrap.querySelector(".vf-view-panel");
  if (!panel || panel.hidden) return;
  panel.hidden = true;
  const toggle = wrap.querySelector(".vf-view-control__toggle");
  if (toggle) toggle.setAttribute("aria-expanded", "false");
}

document.addEventListener("click", e => {
  const wrap = document.getElementById("vf-view-control");
  if (wrap && !wrap.contains(e.target)) vfClosePanel();
});
document.addEventListener("keydown", e => {
  if (e.key === "Escape") vfClosePanel();
});

/* Keep the radios in step after a change made from the banner. */
function vfSyncControl(view) {
  const panel = document.querySelector("#vf-view-control .vf-view-panel");
  if (!panel) return;
  const input = panel.querySelector('input[name="vf-tier"][value="' + view.tier + '"]');
  if (input) input.checked = true;
}

function vfApplyView() {
  const view = vfGetView();
  document.documentElement.dataset.vfTier = view.tier;
  vfPruneNav(view);
  vfRenderBanner(view);
}

function vfInit() {
  if (!window.VF_PAGES) return; /* manifest not loaded */
  vfEnsureControl();
  vfApplyView();
}

/* This file is loaded at the end of <body>, so the nav and header already
   exist: applying now prunes before the first paint instead of letting the
   full navigation flash and then collapse.

   document$ is Material's observable of the current document. It replays to
   late subscribers and emits again on every instant-navigation page swap,
   which is what re-runs the pruning after the theme re-renders the sidebar.
   (There is no "DOMContentSwitch" event — that fires nowhere in the bundle.) */
vfInit();
if (window.document$ && typeof window.document$.subscribe === "function") {
  window.document$.subscribe(vfInit);
} else {
  document.addEventListener("DOMContentLoaded", vfInit);
}
