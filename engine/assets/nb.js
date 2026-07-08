/* The Nightly Build — engine-owned runtime (nb.js).
 *
 * Duties:
 *   1. Appearance: ◐ auto → ○ light → ● dark, persisted in
 *      localStorage("nb-appearance"). Base/no-JS fallback is light (see theme).
 *   2. Declarative charts: renders <script type="application/json"
 *      data-nb-chart> blocks with version-pinned Chart.js from cdnjs — the
 *      ONLY third-party script, loaded here, never by editions.
 *   3. Edition chrome, retrofitted onto every edition ever published:
 *      collapsible Contents, citation source-sheets with backrefs, byline
 *      normalization, desk-linked eyebrow, sequence prev/next from
 *      catalog.json, external links in new tabs.
 *   4. The Search page: scoped fuzzy search over the builder-emitted index.
 *   5. Menu niceties (close on outside tap / Escape).
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
  var MONTHS = [
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
  ];

  /* Site root, derived from this script's own URL (…/assets/nb.js → …/). */
  var script = document.currentScript;
  var ROOT = script ? script.src.replace(/assets\/nb\.js([?#].*)?$/, "") : "./";

  /* ------------------------------------------------------------ appearance */

  /* Verification hook: #light / #dark in the URL forces a mode. Used by the
     screenshot harness; harmless for readers (citation anchors never match). */
  function hashMode() {
    var h = (location.hash || "").replace(/^#/, "").split("&")[0];
    return h === "light" || h === "dark" ? h : null;
  }

  function getAppearance() {
    try {
      var v = localStorage.getItem(APPEARANCE_KEY);
      return MODES.indexOf(v) >= 0 ? v : "auto";
    } catch {
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
    } catch {
      /* private mode: toggle still works for this page */
    }
    applyAppearance(next);
    rerenderCharts();
  }

  applyAppearance(hashMode() || getAppearance());
  window.addEventListener("hashchange", function () {
    var m = hashMode();
    if (m) applyAppearance(m);
  });

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
            labels: {
              color: cssVar("--ink-soft"),
              font: { family: mono, size: 10 },
            },
          },
        },
        scales: {
          x: {
            grid: { color: cssVar("--hair") },
            ticks: {
              color: cssVar("--faint"),
              font: { family: mono, size: 10 },
            },
          },
          y: {
            type: y.scale === "log" ? "logarithmic" : "linear",
            title: y.label
              ? {
                  display: true,
                  text: y.label,
                  color: cssVar("--faint"),
                  font: { family: mono, size: 10 },
                }
              : undefined,
            grid: { color: cssVar("--hair") },
            ticks: {
              color: cssVar("--faint"),
              font: { family: mono, size: 10 },
            },
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
        } catch {
          return; /* the proof blocks malformed charts; never break the page */
        }
        var wrap = canvas.parentElement;
        if (!wrap.classList.contains("nb-chart-box")) {
          wrap = document.createElement("div");
          wrap.className = "nb-chart-box";
          wrap.style.position = "relative";
          wrap.style.height =
            (window.matchMedia("(max-width: 640px)").matches ? 180 : 260) +
            "px";
          canvas.replaceWith(wrap);
          wrap.appendChild(canvas);
        }
        try {
          chartInstances.push(buildChart(canvas, spec));
        } catch {
          /* leave the caption; never break the page */
        }
      });
    });
  }

  function rerenderCharts() {
    if (!chartInstances.length) return;
    chartInstances.forEach(function (c) {
      c.destroy();
    });
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
    chartJsLoading.then(function () {
      if (window.Chart) cb();
    });
  }

  /* --------------------------------------------------------------- catalog */

  var catalogPromise = null;
  function catalog() {
    if (!catalogPromise) {
      catalogPromise = fetch(ROOT + "catalog.json")
        .then(function (r) {
          return r.ok ? r.json() : null;
        })
        .catch(function () {
          return null;
        });
    }
    return catalogPromise;
  }

  function editionUrl(entry) {
    /* catalog paths are site-root-relative ("/library/…"); resolve against ROOT */
    return ROOT + entry.path.replace(/^\//, "");
  }

  /* ---------------------------------------------------------- edition chrome */

  /* Editions are standalone frozen files: the bar and footer that site pages
     get from the builder are injected here, so every edition ever published
     wears the current chrome. Site title comes from catalog.json. */
  function injectChrome() {
    if (document.querySelector(".nb-bar")) return Promise.resolve();
    return catalog().then(function (cat) {
      var title = (cat && cat.site_title) || "The Nightly Build";
      var upstream =
        (cat && cat.upstream) || "the-nightly-build/the-nightly-build";
      var repo = cat && cat.repository;
      var ext = 'target="_blank" rel="noopener noreferrer"';
      /* Ecosystem links under the nav (mirrors build_site.chrome_eco_links).
         Star this press is omitted when the repo is unknown; no network link
         yet, since the directory site is not live. */
      var eco = repo
        ? '<a href="https://github.com/' +
          repo +
          '" ' +
          ext +
          ">Star this press on GitHub ↗</a>"
        : "";
      eco +=
        '<a href="https://github.com/' +
        upstream +
        '" ' +
        ext +
        ">Make your own press ↗</a>";
      var imprint =
        cat && cat.footer
          ? '<span class="nb-imprint">' + escHtml(cat.footer) + "</span>"
          : '<a class="nb-imprint" href="https://github.com/' +
            upstream +
            '" ' +
            ext +
            ">A Nightly Build press</a>";
      var bar = document.createElement("header");
      bar.className = "nb-bar";
      bar.innerHTML =
        '<div class="nb-bar-in"><a class="nb-wordmark" href="' +
        ROOT +
        '">' +
        escHtml(title) +
        '<span class="nb-period">.</span></a>' +
        '<details class="nb-menu"><summary aria-label="Menu">' +
        '<span class="nb-burger"></span></summary>' +
        '<nav class="nb-menu-panel"><div class="nb-menu-nav">' +
        '<a href="' +
        ROOT +
        '">Today</a>' +
        '<a href="' +
        ROOT +
        'series/">Sections</a>' +
        '<a href="' +
        ROOT +
        'search/">Search</a>' +
        '<a href="' +
        ROOT +
        'feed.xml">RSS</a></div>' +
        '<div class="nb-menu-eco">' +
        eco +
        "</div></nav></details></div>";
      document.body.insertBefore(bar, document.body.firstChild);
      var foot = document.createElement("footer");
      foot.className = "nb-footer";
      foot.innerHTML =
        '<div class="nb-footer-in">' +
        imprint +
        '<button class="nb-appearance" type="button">◐ auto</button></div>';
      document.body.appendChild(foot);
    });
  }

  function editionMeta() {
    var el = document.getElementById("nb-meta");
    if (!el) return null;
    try {
      var meta = JSON.parse(el.textContent);
      return typeof meta === "object" && meta ? meta : null;
    } catch {
      return null;
    }
  }

  function prettyDate(iso) {
    var m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(iso || "");
    if (!m) return iso;
    return (
      MONTHS[parseInt(m[2], 10) - 1] + " " + parseInt(m[3], 10) + ", " + m[1]
    );
  }

  function buildToc() {
    var items = [];
    document.querySelectorAll("section[data-nb-section]").forEach(function (s) {
      var h = s.querySelector("h2");
      if (!h) return;
      if (!s.id) s.id = "nb-" + s.getAttribute("data-nb-section");
      items.push({
        id: s.id,
        label: h.textContent.replace(/^\s*\d+\s*/, "").trim(),
      });
    });
    if (items.length < 3) return;
    var d = document.createElement("details");
    d.className = "nb-toc";
    d.innerHTML =
      "<summary>Contents</summary><ol>" +
      items
        .map(function (i) {
          return '<li><a href="#' + i.id + '">' + i.label + "</a></li>";
        })
        .join("") +
      "</ol>";
    var byline = document.querySelector(".nb-byline");
    if (byline && byline.parentNode)
      byline.parentNode.insertBefore(d, byline.nextSibling);
  }

  function normalizeByline() {
    document.querySelectorAll(".nb-byline span").forEach(function (s) {
      var txt = s.textContent.trim();
      if (/min read/i.test(txt)) return;
      if (/^\d{4}-\d{2}-\d{2}$/.test(txt)) {
        s.textContent = prettyDate(txt);
        s.classList.add("nb-date");
        return;
      }
      if (s.classList.contains("nb-date")) return;
      s.classList.add("nb-hide");
    });
  }

  function linkEyebrow(meta) {
    var eyebrow = document.querySelector(".nb-eyebrow");
    if (!eyebrow || !meta.series || eyebrow.querySelector("a")) return;
    var wrap = document.createElement("a");
    wrap.href = ROOT + "series/" + meta.series + "/";
    while (eyebrow.firstChild) wrap.appendChild(eyebrow.firstChild);
    eyebrow.appendChild(wrap);
  }

  /* citations: tap opens a source sheet; sources gain ↩ backrefs */
  var veil = null;
  function closeSheet() {
    if (veil) {
      veil.remove();
      veil = null;
    }
    var s = document.querySelector(".nb-sheet");
    if (s) s.remove();
  }

  function openSheet(num, li) {
    closeSheet();
    veil = document.createElement("div");
    veil.className = "nb-veil";
    veil.addEventListener("click", closeSheet);
    var body = li.cloneNode(true);
    body.querySelectorAll(".nb-backref").forEach(function (b) {
      b.remove();
    });
    body.querySelectorAll("a").forEach(function (a) {
      a.target = "_blank";
      a.rel = "noopener";
    });
    var sheet = document.createElement("div");
    sheet.className = "nb-sheet";
    sheet.innerHTML =
      '<div class="nb-sheet-label">Source ' +
      num +
      "</div>" +
      '<div class="nb-sheet-body">' +
      body.innerHTML +
      "</div>";
    document.body.appendChild(veil);
    document.body.appendChild(sheet);
  }

  function normalizeSources() {
    document.querySelectorAll(".nb-sources li").forEach(function (li) {
      var a = li.querySelector("a[data-nb-source]");
      if (!a || a.textContent.trim().toLowerCase() !== "link") return;
      var parts = [];
      var node = li.firstChild;
      while (node && node !== a) {
        parts.push(node.textContent);
        var next = node.nextSibling;
        li.removeChild(node);
        node = next;
      }
      var title = parts
        .join("")
        .replace(/[.\s]+$/, "")
        .trim();
      if (title) a.textContent = title;
    });
  }

  function bindCitations() {
    var firstCiter = {};
    document.querySelectorAll("sup.nb-cite a").forEach(function (a, i) {
      var target = (a.getAttribute("href") || "").slice(1);
      if (!target) return;
      if (!a.id) a.id = "cite-" + target + (firstCiter[target] ? "-" + i : "");
      if (!firstCiter[target]) firstCiter[target] = a.id;
      a.addEventListener("click", function (e) {
        var li = document.getElementById(target);
        if (!li) return;
        e.preventDefault();
        openSheet(a.textContent.trim(), li);
      });
    });
    Object.keys(firstCiter).forEach(function (target) {
      var li = document.getElementById(target);
      if (!li || li.querySelector(".nb-backref")) return;
      var back = document.createElement("a");
      back.className = "nb-backref";
      back.href = "#" + firstCiter[target];
      back.textContent = "↩";
      back.setAttribute("aria-label", "back to text");
      li.appendChild(document.createTextNode(" "));
      li.appendChild(back);
    });
    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape") closeSheet();
    });
  }

  /* sequences: prev/next when a published neighbor exists; nothing else */
  function bindSequenceNav(meta) {
    if (meta.mode !== "sequence" || !meta.order) return;
    catalog().then(function (cat) {
      if (!cat) return;
      var sibs = (cat.editions || []).filter(function (e) {
        return e.series === meta.series && e.order;
      });
      var prev = sibs.find(function (e) {
        return e.order === meta.order - 1;
      });
      var next = sibs.find(function (e) {
        return e.order === meta.order + 1;
      });
      if (!prev && !next) return;
      function link(e, arrow) {
        return (
          '<a href="' +
          editionUrl(e) +
          '">' +
          (arrow === "l" ? "← " : "") +
          e.title +
          (arrow === "r" ? " →" : "") +
          "</a>"
        );
      }
      var nav = document.createElement("nav");
      nav.className = "nb-endnav";
      nav.innerHTML =
        '<div class="nb-endnav-row">' +
        (prev ? link(prev, "l") : "<span></span>") +
        (next ? link(next, "r") : "<span></span>") +
        "</div>";
      (document.querySelector("article") || document.body).appendChild(nav);
    });
  }

  /* ---------------------------------------------------------------- search */

  function fuzzy(needle, hay) {
    var i = 0;
    for (var j = 0; j < hay.length && i < needle.length; j++) {
      if (hay[j] === needle[i]) i++;
    }
    if (i < needle.length) return 0;
    /* tightest window from the end backwards → 1.0 means a contiguous run */
    var end = -1,
      start = -1;
    i = needle.length - 1;
    for (var k = hay.length - 1; k >= 0 && i >= 0; k--) {
      if (hay[k] === needle[i]) {
        if (end < 0) end = k;
        start = k;
        i--;
      }
    }
    return needle.length / Math.max(end - start + 1, needle.length);
  }

  function escHtml(s) {
    return String(s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;");
  }

  function initSearch() {
    var input = document.getElementById("nb-q");
    var out = document.getElementById("nb-results");
    var count = document.getElementById("nb-count");
    if (!input || !out) return;
    var docs = [];

    fetch(ROOT + "search-index.json")
      .then(function (r) {
        return r.ok ? r.json() : [];
      })
      .catch(function () {
        return [];
      })
      .then(function (index) {
        docs = index.map(function (e) {
          return {
            e: e,
            title: (e.title || "").toLowerCase(),
            dek: (e.dek || "").toLowerCase(),
            desk: (
              (e.section || "") +
              " " +
              (e.series_name || e.series || "")
            ).toLowerCase(),
            tags: (e.tags || []).join(" ").toLowerCase(),
            text: (e.text || "").toLowerCase(),
          };
        });
        render();
        prefill();
      });

    function prefill() {
      var p = new URLSearchParams(location.search);
      if (p.get("q")) {
        input.value = p.get("q");
        render();
      }
      input.focus();
    }

    function scoreDoc(d, tokens) {
      /* one search over everything: titles, deks, desks, tags, full text */
      var total = 0;
      for (var t = 0; t < tokens.length; t++) {
        var q = tokens[t],
          s = 0;
        if (d.title.indexOf(q) >= 0) s = Math.max(s, 6);
        else s = Math.max(s, fuzzy(q, d.title) * 3);
        if (d.dek.indexOf(q) >= 0) s = Math.max(s, 3);
        if (d.desk.indexOf(q) >= 0) s = Math.max(s, 4);
        else s = Math.max(s, fuzzy(q, d.desk) * 2);
        if (d.tags && d.tags.indexOf(q) >= 0) s = Math.max(s, 4);
        if (d.text && d.text.indexOf(q) >= 0) s = Math.max(s, 2);
        if (s <= 0.34) return 0; /* every token must land somewhere */
        total += s;
      }
      return total;
    }

    function snippet(d, tokens) {
      for (var t = 0; t < tokens.length; t++) {
        var i = d.text.indexOf(tokens[t]);
        if (i >= 0) {
          var from = Math.max(0, i - 80);
          var raw =
            (from > 0 ? "…" : "") + (d.e.text || "").slice(from, i + 100) + "…";
          var safe = escHtml(raw);
          tokens.forEach(function (q) {
            safe = safe.replace(
              new RegExp(
                "(" + q.replace(/[.*+?^${}()|[\]\\]/g, "\\$&") + ")",
                "ig",
              ),
              "<mark>$1</mark>",
            );
          });
          return safe;
        }
      }
      return escHtml(d.e.dek || "");
    }

    function renderRecent() {
      /* empty query: the newest editions under month labels, not a dump */
      var recent = docs.slice(0, 20);
      if (count) count.textContent = "";
      var seen = null;
      out.innerHTML = recent
        .map(function (d) {
          var e = d.e;
          var month = (e.date || "").slice(0, 7);
          var label = "";
          if (month && month !== seen) {
            seen = month;
            var mm = MONTHS[parseInt(month.slice(5), 10) - 1] || month;
            label =
              '<span class="nb-month-label">' +
              mm +
              " " +
              month.slice(0, 4) +
              "</span>";
          }
          return label + resultRow(d, []);
        })
        .join("");
    }

    function resultRow(d, tokens) {
      var e = d.e;
      var kicker = e.section
        ? e.section + " — " + (e.series_name || e.series)
        : e.series_name || e.series;
      var body =
        tokens.length && d.text ? snippet(d, tokens) : escHtml(e.dek || "");
      return (
        '<a class="nb-item" href="' +
        editionUrl(e) +
        '">' +
        '<div class="nb-kicker">' +
        escHtml(kicker) +
        "</div>" +
        "<h3>" +
        escHtml(e.title || e.slug) +
        "</h3>" +
        '<p class="nb-snippet">' +
        body +
        "</p>" +
        '<div class="nb-meta"><span>' +
        (e.reading_minutes || "?") +
        " min read</span><span>" +
        escHtml(
          String(e.template || "")
            .charAt(0)
            .toUpperCase() + String(e.template || "").slice(1),
        ) +
        "</span></div></a>"
      );
    }

    function render() {
      var q = (input.value || "").trim().toLowerCase();
      var tokens = q ? q.split(/\s+/) : [];
      if (!tokens.length) return renderRecent();
      var hits = docs
        .map(function (d) {
          return { d: d, score: scoreDoc(d, tokens) };
        })
        .filter(function (h) {
          return h.score > 0;
        });
      hits.sort(function (a, b) {
        return b.score - a.score;
      });
      if (count) {
        count.textContent =
          hits.length +
          " of " +
          docs.length +
          " edition" +
          (docs.length !== 1 ? "s" : "");
      }
      out.innerHTML =
        hits
          .map(function (h) {
            return resultRow(h.d, tokens);
          })
          .join("") ||
        '<div class="nb-results-count" style="padding:20px 0">No matches.</div>';
    }

    var timer = null;
    input.addEventListener("input", function () {
      clearTimeout(timer);
      timer = setTimeout(render, 90);
    });
  }

  /* ------------------------------------------------------------------ init */

  function bindChrome() {
    document.querySelectorAll(".nb-appearance").forEach(function (btn) {
      if (btn.dataset.nbBound) return;
      btn.dataset.nbBound = "1";
      btn.addEventListener("click", cycleAppearance);
    });
    applyAppearance(hashMode() || getAppearance());
    var menu = document.querySelector(".nb-menu");
    if (menu && !menu.dataset.nbBound) {
      menu.dataset.nbBound = "1";
      document.addEventListener("click", function (e) {
        if (menu.open && !(e.target.closest && e.target.closest(".nb-menu"))) {
          menu.open = false;
        }
      });
      document.addEventListener("keydown", function (e) {
        if (e.key === "Escape") menu.open = false;
      });
    }
    document.querySelectorAll('a[href^="http"]').forEach(function (a) {
      if (a.host === location.host) return; /* internal: stay in-tab */
      a.target = "_blank";
      a.rel = "noopener";
    });
  }

  function init() {
    bindChrome();
    renderCharts();

    var meta = editionMeta();
    if (meta) {
      injectChrome().then(bindChrome);
      buildToc();
      normalizeByline();
      linkEyebrow(meta);
      normalizeSources();
      bindCitations();
      bindSequenceNav(meta);
    }

    initSearch();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
