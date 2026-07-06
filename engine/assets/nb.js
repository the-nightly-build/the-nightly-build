/* The Nightly Build — engine-owned runtime (nb.js).
 *
 * Duties:
 *   1. Appearance toggle: ◐ auto → ○ light → ● dark, persisted in
 *      localStorage("nb-appearance"). Base/no-JS fallback is light (see theme).
 *   2. Declarative chart renderer: finds <script type="application/json"
 *      data-nb-chart> blocks and renders them with version-pinned Chart.js from
 *      cdnjs — the ONLY third-party script, loaded here, never by editions.
 *   3. Contextual nav injected into editions (back to tonight, series progress,
 *      prev/next edition, tag links), driven by catalog.json.
 *   4. Client-side search over catalog.json from the masthead.
 *
 * Must degrade gracefully: with no JS the site is a clean readable document.
 */
(function () {
  "use strict";

  var CHARTJS_URL =
    "https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.min.js";
  var APPEARANCE_KEY = "nb-appearance";
  var MODES = ["auto", "light", "dark"];
  var GLYPHS = { auto: "◐ auto", light: "○ light", dark: "● dark" };

  /* Site root, derived from this script's own URL (…/assets/nb.js → …/). */
  var script = document.currentScript;
  var ROOT = script
    ? script.src.replace(/assets\/nb\.js([?#].*)?$/, "")
    : "./";

  /* ------------------------------------------------------------ appearance */

  function getAppearance() {
    try {
      var v = localStorage.getItem(APPEARANCE_KEY);
      return MODES.indexOf(v) >= 0 ? v : "auto";
    } catch (e) {
      return "auto";
    }
  }

  function applyAppearance(mode) {
    var root = document.documentElement;
    if (mode === "auto") root.removeAttribute("data-mode");
    else root.setAttribute("data-mode", mode);
    document.querySelectorAll(".nb-appearance").forEach(function (btn) {
      btn.textContent = GLYPHS[mode];
      btn.setAttribute("aria-label", "appearance: " + mode);
    });
  }

  function cycleAppearance() {
    var next = MODES[(MODES.indexOf(getAppearance()) + 1) % MODES.length];
    try {
      localStorage.setItem(APPEARANCE_KEY, next);
    } catch (e) { /* private mode: toggle still works for this page */ }
    applyAppearance(next);
    rerenderCharts();
  }

  applyAppearance(getAppearance());

  /* ---------------------------------------------------------------- charts */

  var chartInstances = [];

  function cssVar(name) {
    return getComputedStyle(document.documentElement)
      .getPropertyValue(name)
      .trim();
  }

  function chartColors() {
    return [cssVar("--accent"), cssVar("--accent-2"), cssVar("--ink-soft")];
  }

  function buildChart(canvas, spec) {
    var colors = chartColors();
    var mono = cssVar("--mono") || "monospace";
    var scatter = spec.type === "scatter";
    var datasets = (spec.series || []).map(function (s, i) {
      var color = colors[i % colors.length];
      return {
        label: s.name,
        data: scatter
          ? s.values.map(function (v, j) {
              return { x: Number(spec.labels[j]), y: v };
            })
          : s.values,
        borderColor: color,
        backgroundColor: spec.type === "bar" ? color : color + "33",
        borderWidth: 2,
        pointRadius: scatter ? 3.5 : 2,
        tension: 0.25,
      };
    });
    var y = spec.y || {};
    return new Chart(canvas, {
      type: spec.type,
      data: { labels: spec.labels, datasets: datasets },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            display: datasets.length > 1,
            labels: { color: cssVar("--ink-soft"), font: { family: mono, size: 10 } },
          },
        },
        scales: {
          x: {
            grid: { color: cssVar("--hair") },
            ticks: { color: cssVar("--faint"), font: { family: mono, size: 10 } },
          },
          y: {
            type: y.scale === "log" ? "logarithmic" : "linear",
            title: y.label
              ? { display: true, text: y.label, color: cssVar("--faint"),
                  font: { family: mono, size: 10 } }
              : undefined,
            grid: { color: cssVar("--hair") },
            ticks: { color: cssVar("--faint"), font: { family: mono, size: 10 } },
          },
        },
      },
    });
  }

  function renderCharts() {
    var blocks = document.querySelectorAll("script[data-nb-chart]");
    if (!blocks.length) return;
    loadChartJs(function () {
      blocks.forEach(function (block) {
        var fig = block.closest("figure") || block.parentElement;
        var canvas = fig && fig.querySelector("canvas");
        if (!canvas) return;
        var spec;
        try {
          spec = JSON.parse(block.textContent);
        } catch (e) {
          return; /* the proof blocks malformed charts; never break the page */
        }
        var wrap = canvas.parentElement;
        if (!wrap.classList.contains("nb-chart-box")) {
          wrap = document.createElement("div");
          wrap.className = "nb-chart-box";
          wrap.style.position = "relative";
          wrap.style.height =
            (window.matchMedia("(max-width: 640px)").matches ? 180 : 260) + "px";
          canvas.replaceWith(wrap);
          wrap.appendChild(canvas);
        }
        try {
          chartInstances.push(buildChart(canvas, spec));
        } catch (e) { /* leave the caption; never break the page */ }
      });
    });
  }

  function rerenderCharts() {
    if (!chartInstances.length) return;
    chartInstances.forEach(function (c) { c.destroy(); });
    chartInstances = [];
    renderCharts();
  }

  var chartJsLoading = null;
  function loadChartJs(cb) {
    if (window.Chart) return cb();
    if (!chartJsLoading) {
      chartJsLoading = new Promise(function (resolve) {
        var s = document.createElement("script");
        s.src = CHARTJS_URL;
        s.onload = resolve;
        s.onerror = resolve; /* offline: captions still readable */
        document.head.appendChild(s);
      });
    }
    chartJsLoading.then(function () { if (window.Chart) cb(); });
  }

  /* --------------------------------------------------------------- catalog */

  var catalogPromise = null;
  function catalog() {
    if (!catalogPromise) {
      catalogPromise = fetch(ROOT + "catalog.json")
        .then(function (r) { return r.ok ? r.json() : null; })
        .catch(function () { return null; });
    }
    return catalogPromise;
  }

  function editionUrl(entry) {
    /* catalog paths are site-root-relative ("/library/…"); resolve against ROOT */
    return ROOT + entry.path.replace(/^\//, "");
  }

  /* --------------------------------------------- contextual nav (editions) */

  function editionMeta() {
    var el = document.getElementById("nb-meta");
    if (!el) return null;
    try {
      return JSON.parse(el.textContent);
    } catch (e) {
      return null;
    }
  }

  function seriesEditions(cat, seriesId) {
    return cat.editions
      .filter(function (e) { return e.series === seriesId; })
      .sort(function (a, b) { return (a.position || 0) - (b.position || 0); });
  }

  function injectEditionNav(meta) {
    catalog().then(function (cat) {
      if (!cat) return;
      var sibs = seriesEditions(cat, meta.series);
      var idx = sibs.findIndex(function (e) { return e.slug === meta.slug; });
      var sinfo = (cat.series || []).find(function (s) { return s.id === meta.series; });

      var nav = document.createElement("nav");
      nav.className = "nb-context-nav nb-wrap";

      var topRow = document.createElement("div");
      topRow.className = "nb-context-row";
      topRow.innerHTML =
        '<a href="' + ROOT + '">← Tonight’s build</a>' +
        '<a href="' + ROOT + "series/" + meta.series + '/">' +
        (sinfo ? sinfo.name : meta.series) +
        (sinfo && meta.mode === "sequence" && sinfo.total
          ? " · Ed. " + (idx + 1) + " of " + sinfo.total
          : "") +
        "</a>";
      nav.appendChild(topRow);

      if (idx >= 0 && sibs.length > 1) {
        var pager = document.createElement("div");
        pager.className = "nb-context-row";
        var prev = idx > 0 ? sibs[idx - 1] : null;
        var next = idx < sibs.length - 1 ? sibs[idx + 1] : null;
        pager.innerHTML =
          (prev
            ? '<a href="' + editionUrl(prev) + '">← ' + prev.title + "</a>"
            : "<span></span>") +
          (next
            ? '<a href="' + editionUrl(next) + '">' + next.title + " →</a>"
            : "<span></span>");
        nav.appendChild(pager);
      }

      if (meta.tags && meta.tags.length) {
        var tags = document.createElement("div");
        tags.className = "nb-context-row";
        tags.innerHTML = meta.tags
          .map(function (t) {
            return '<a href="' + ROOT + "tags/" + t + '/">#' + t + "</a>";
          })
          .join(" ");
        nav.appendChild(tags);
      }

      document.body.appendChild(nav);
    });
  }

  /* ---------------------------------------------------------------- search */

  function bindSearch() {
    var box = document.querySelector(".nb-search");
    if (!box) return;
    var input = box.querySelector("input");
    var results = box.querySelector(".nb-search-results");
    if (!input || !results) return;

    var timer = null;
    input.addEventListener("input", function () {
      clearTimeout(timer);
      timer = setTimeout(function () {
        var q = input.value.trim().toLowerCase();
        if (!q) { results.innerHTML = ""; return; }
        catalog().then(function (cat) {
          if (!cat) return;
          var hits = cat.editions.filter(function (e) {
            return (
              (e.title || "").toLowerCase().indexOf(q) >= 0 ||
              (e.dek || "").toLowerCase().indexOf(q) >= 0 ||
              (e.series || "").toLowerCase().indexOf(q) >= 0 ||
              (e.tags || []).some(function (t) {
                return t.toLowerCase().indexOf(q) >= 0;
              })
            );
          }).slice(0, 12);
          results.innerHTML = hits.length
            ? hits.map(function (e) {
                return (
                  '<a href="' + editionUrl(e) + '"><span class="t">' + e.title +
                  '</span><br><span class="m">' + e.series + " · " + e.date +
                  "</span></a>"
                );
              }).join("")
            : '<div class="nb-search-empty">no matches</div>';
        });
      }, 120);
    });
    document.addEventListener("click", function (ev) {
      if (!box.contains(ev.target)) results.innerHTML = "";
    });
  }

  /* ------------------------------------------------------------- deck keys */

  function bindDeck() {
    var deck = document.querySelector(".nb-deck");
    if (!deck) return;
    document.addEventListener("keydown", function (ev) {
      if (ev.key !== "ArrowRight" && ev.key !== "ArrowLeft") return;
      var slide = deck.querySelector(".nb-slide");
      if (!slide) return;
      ev.preventDefault();
      var dx = slide.getBoundingClientRect().width + 14;
      deck.scrollBy({
        left: ev.key === "ArrowRight" ? dx : -dx,
        behavior: "smooth",
      });
    });
  }

  /* ------------------------------------------------------------------ init */

  function init() {
    document.querySelectorAll(".nb-appearance").forEach(function (btn) {
      btn.addEventListener("click", cycleAppearance);
    });
    applyAppearance(getAppearance());

    var meta = editionMeta();
    if (meta) injectEditionNav(meta);

    renderCharts();
    bindSearch();
    bindDeck();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
