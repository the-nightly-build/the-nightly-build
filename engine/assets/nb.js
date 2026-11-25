/* The Nightly Build — engine-owned runtime (nb.js).
 *
 * Duties:
 *   1. Appearance: ◐ auto → ○ light → ● dark, persisted in
 *      localStorage("nb-appearance"). Base/no-JS fallback is light (see theme).
 *   2. Vendor libraries for furniture that needs one, loaded here, never by
 *      articles: KaTeX typesets nb-math, Shiki highlights nb-code listings,
 *      and Chart.js draws legacy declarative charts. Each loads only when the
 *      page carries the furniture.
 *   3. Article furniture, retrofitted onto every article ever published:
 *      collapsible Contents, citation source-sheets with backrefs, byline
 *      normalization, series-linked eyebrow, series last/next from
 *      catalog.json, external links in new tabs. The bar and footer are not
 *      here: the builder splices them into the article copy it publishes.
 *   4. The Search page: scoped fuzzy search over the builder-emitted index.
 *   5. Menu niceties (close on outside tap / Escape).
 *
 * Must degrade gracefully: with no JS the site is a clean readable document.
 */
(function () {
  "use strict";

  const CHARTJS_URL =
    "https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.min.js";
  const APPEARANCE_KEY = "nb-appearance";
  const MODES = ["auto", "light", "dark"];
  const GLYPHS = { auto: "◐ auto", light: "○ light", dark: "● dark" };
  const MONTHS = [
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
  const script = document.currentScript;
  const ROOT = script
    ? script.src.replace(/assets\/nb\.js([?#].*)?$/, "")
    : "./";

  /* ------------------------------------------------------------ appearance */

  /* Verification hook: #light / #dark in the URL forces a mode. Used by the
     screenshot harness; harmless for readers (citation anchors never match). */
  function hashMode() {
    const h = (location.hash || "").replace(/^#/, "").split("&")[0];
    return h === "light" || h === "dark" ? h : null;
  }

  function getAppearance() {
    try {
      const v = localStorage.getItem(APPEARANCE_KEY);
      return MODES.indexOf(v) >= 0 ? v : "auto";
    } catch {
      return "auto";
    }
  }

  function applyAppearance(mode) {
    const root = document.documentElement;
    if (mode === "auto") root.removeAttribute("data-mode");
    else root.setAttribute("data-mode", mode);
    document.querySelectorAll(".nb-appearance").forEach(function (btn) {
      btn.textContent = GLYPHS[mode];
      btn.setAttribute("aria-label", "appearance: " + mode);
    });
  }

  function cycleAppearance() {
    const next = MODES[(MODES.indexOf(getAppearance()) + 1) % MODES.length];
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
    const m = hashMode();
    if (m) applyAppearance(m);
  });

  /* ------------------------------------------------- legacy charts
   * data-nb-chart blocks are retired for new articles (charts are PNGs
   * rendered by engine/render_chart.py); this renderer stays so the
   * published shelf keeps drawing. Chart.js loads only when a legacy
   * block exists on the page. */

  let chartInstances = [];

  function cssVar(name) {
    return getComputedStyle(document.documentElement)
      .getPropertyValue(name)
      .trim();
  }

  function chartColors() {
    const slots = [];
    for (let i = 1; i <= 6; i++) {
      const c = cssVar("--chart-" + i);
      if (c) slots.push(c);
    }
    if (slots.length) return slots;
    /* themes older than the chart tokens keep rendering on the accent trio */
    return [cssVar("--accent"), cssVar("--accent-2"), cssVar("--ink-soft")];
  }

  function buildChart(canvas, spec) {
    const colors = chartColors();
    const font = { family: cssVar("--mono") || "monospace", size: 10 };
    const hair = cssVar("--hair");
    const faint = cssVar("--faint");
    const scatter = spec.type === "scatter";
    const datasets = (spec.series || []).map(function (s, i) {
      const color = colors[i % colors.length];
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
    const y = spec.y || {};
    return new Chart(canvas, {
      type: spec.type,
      data: { labels: spec.labels, datasets: datasets },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            display: datasets.length > 1,
            labels: { color: cssVar("--ink-soft"), font: font },
          },
        },
        scales: {
          x: {
            grid: { color: hair },
            ticks: { color: faint, font: font },
          },
          y: {
            type: y.scale === "log" ? "logarithmic" : "linear",
            title: y.label
              ? { display: true, text: y.label, color: faint, font: font }
              : undefined,
            grid: { color: hair },
            ticks: { color: faint, font: font },
          },
        },
      },
    });
  }

  function renderCharts() {
    const blocks = document.querySelectorAll("script[data-nb-chart]");
    if (!blocks.length) return;
    loadChartJs(function () {
      blocks.forEach(function (block) {
        const fig = block.closest("figure") || block.parentElement;
        const canvas = fig && fig.querySelector("canvas");
        if (!canvas) return;
        let spec;
        try {
          spec = JSON.parse(block.textContent);
        } catch {
          return; /* the proof blocks malformed charts; never break the page */
        }
        let wrap = canvas.parentElement;
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

  let chartJsLoading = null;
  function loadChartJs(cb) {
    if (window.Chart) return cb();
    if (!chartJsLoading) {
      chartJsLoading = new Promise(function (resolve) {
        const s = document.createElement("script");
        s.src = CHARTJS_URL;
        s.addEventListener("load", resolve);
        s.addEventListener(
          "error",
          resolve,
        ); /* offline: captions still readable */
        document.head.appendChild(s);
      });
    }
    chartJsLoading.then(function () {
      if (window.Chart) cb();
    });
  }

  /* ------------------------------------------------- math + code furniture
   * The source remains readable when JavaScript or a CDN is unavailable. */

  /* KaTeX rides jsdelivr, not cdnjs like the others: its webfonts load
     relative to the CSS, and cdnjs serves them as octet-stream, which
     Chrome refuses for font loads. jsdelivr serves font/woff2. */
  const KATEX_CSS = {
    url: "https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/katex.min.css",
    integrity:
      "sha384-nB0miv6/jRmo5UMMR1wu3Gz6NLsoTkbqJghGIsx//Rlm+ZU03BU6SQNC66uf4l5+",
  };
  const KATEX_JS = {
    url: "https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/katex.min.js",
    integrity:
      "sha384-7zkQWkzuo3B5mTepMUcHkMB5jZaolc2xDwL6VFqjFALcbeS9Ggm/Yr2r3Dy4lfFg",
  };
  const SHIKI_URL = "https://esm.sh/shiki@3.12.2";
  let shikiTask;

  function loadVendorAsset(tag, spec) {
    return new Promise(function (resolve) {
      const el = document.createElement(tag);
      if (tag === "link") {
        el.rel = "stylesheet";
        el.href = spec.url;
      } else {
        el.src = spec.url;
      }
      el.integrity = spec.integrity;
      el.crossOrigin = "anonymous";
      el.referrerPolicy = "no-referrer";
      el.addEventListener("load", resolve);
      el.addEventListener(
        "error",
        resolve,
      ); /* offline: fallback text stays readable */
      document.head.appendChild(el);
    });
  }

  /* A press-declared copy of a library (site.yaml assets, injected into
     head) outranks the engine's: same trust model, the press's version. */
  function pressCopy(lib) {
    return document.querySelector('script[src*="' + lib + '"]');
  }

  function typesetMath(els) {
    els.forEach(function (el) {
      if (el.querySelector(".katex")) return; /* already typeset */
      try {
        window.katex.render(el.textContent, el, {
          displayMode: el.classList.contains("nb-math-eq"),
          throwOnError: false,
          strict: "ignore",
          output: "htmlAndMathml",
          /* \htmlClass only, for the annotated form's term colors: the
             class lands on a span and nb.css colors it from the chart
             tokens. Nothing else in the trust surface is enabled. */
          trust: function (ctx) {
            return ctx.command === "\\htmlClass";
          },
        });
      } catch {
        /* malformed TeX: the source stays visible; never break the page */
      }
    });
  }

  function renderMath() {
    const els = document.querySelectorAll(
      ".nb-math-eq, .nb-math-in, .nb-math-term",
    );
    if (!els.length) return;
    if (window.katex) return typesetMath(els);
    const press = pressCopy("katex");
    if (press) {
      /* deferred press scripts execute after nb.js: typeset once it lands */
      press.addEventListener("load", function () {
        if (window.katex) typesetMath(els);
      });
      return;
    }
    Promise.all([
      loadVendorAsset("link", KATEX_CSS),
      loadVendorAsset("script", KATEX_JS),
    ]).then(function () {
      if (window.katex) typesetMath(els);
    });
  }

  function highlightBlock(shiki, code) {
    const source = code.textContent.replace(/^\n/, "").replace(/\n[ \t]*$/, "");
    const lang =
      code.dataset.language ||
      (code.className.match(/(?:^|\s)language-([\w-]+)/) || [])[1] ||
      "text";
    shiki
      .codeToHtml(source, {
        lang: lang,
        themes: { light: "github-light", dark: "github-dark" },
        defaultColor: false,
      })
      .then(function (html) {
        if (!code.isConnected) return;
        const holder = document.createElement("div");
        holder.innerHTML = html;
        const rendered = holder.querySelector("pre.shiki");
        if (rendered) code.parentElement.replaceWith(rendered);
      })
      .catch(function () {
        /* Unknown grammar: keep the authored source. */
      });
  }

  function highlightCode() {
    const blocks = document.querySelectorAll(
      '.nb-code pre code[data-language], .nb-code pre code[class*="language-"]',
    );
    if (!blocks.length) return;
    shikiTask = shikiTask || import(SHIKI_URL);
    shikiTask
      .then(function (shiki) {
        blocks.forEach(function (code) {
          highlightBlock(shiki, code);
        });
      })
      .catch(function () {
        /* Offline: keep every listing as plain source. */
      });
  }

  /* Every nb-table rides in the data-block card. The authored markup is
     the bare table (caption inside), so the runtime dresses each one:
     card > scroll container > table, the caption re-seated as the card's
     figcaption footer. Nodes are moved, never re-parsed, so citation
     markup survives untouched, and the whole published shelf retrofits.
     No JS: the bare table is its own scroll container (see nb.css). */
  function dressTables() {
    document.querySelectorAll("table.nb-table").forEach(function (tbl) {
      if (tbl.closest(".nb-table-card")) return; /* already dressed */
      const card = document.createElement("figure");
      card.className = "nb-table-card";
      const scroll = document.createElement("div");
      scroll.className = "nb-table-scroll";
      tbl.parentNode.insertBefore(card, tbl);
      scroll.appendChild(tbl);
      card.appendChild(scroll);
      const cap = tbl.caption;
      if (cap) {
        const foot = document.createElement("figcaption");
        while (cap.firstChild) foot.appendChild(cap.firstChild);
        cap.remove();
        card.appendChild(foot);
      }
    });
  }

  /* --------------------------------------------------------------- catalog */

  let catalogPromise = null;
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

  function articleUrl(entry) {
    /* catalog paths are site-root-relative ("/library/…"); resolve against ROOT */
    return ROOT + entry.path.replace(/^\//, "");
  }

  function articleMeta() {
    const el = document.getElementById("nb-meta");
    if (!el) return null;
    try {
      const meta = JSON.parse(el.textContent);
      return typeof meta === "object" && meta ? meta : null;
    } catch {
      return null;
    }
  }

  function prettyDate(iso) {
    const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(iso || "");
    if (!m) return iso;
    return (
      MONTHS[parseInt(m[2], 10) - 1] + " " + parseInt(m[3], 10) + ", " + m[1]
    );
  }

  /* nested <ol> from items in document order: a deeper heading level opens a
     sublist inside the shallower item above it */
  function tocList(items) {
    let html = "";
    const levels = [];
    items.forEach(function (i) {
      if (!levels.length || i.level > levels[levels.length - 1]) {
        html += "<ol>";
        levels.push(i.level);
      } else {
        html += "</li>";
        while (levels.length > 1 && i.level < levels[levels.length - 1]) {
          html += "</ol></li>";
          levels.pop();
        }
      }
      html +=
        '<li><a href="#' + escHtml(i.id) + '">' + escHtml(i.label) + "</a>";
    });
    html += "</li>";
    while (levels.length > 1) {
      html += "</ol></li>";
      levels.pop();
    }
    return html + "</ol>";
  }

  function buildToc() {
    const items = [];
    document.querySelectorAll("section[data-nb-section]").forEach(function (s) {
      const h = s.querySelector("h1,h2,h3,h4,h5,h6");
      if (!h) return;
      if (!s.id) s.id = "nb-" + s.getAttribute("data-nb-section");
      items.push({
        id: s.id,
        level: parseInt(h.tagName.slice(1), 10),
        label: h.textContent.replace(/^\s*\d+\s*/, "").trim(),
      });
    });
    if (items.length < 3) return;
    const d = document.createElement("details");
    d.className = "nb-toc";
    d.innerHTML = "<summary>Contents</summary>" + tocList(items);
    const byline = document.querySelector(".nb-byline");
    if (byline && byline.parentNode) {
      byline.parentNode.insertBefore(d, byline.nextSibling);
    }
  }

  function normalizeByline() {
    document.querySelectorAll(".nb-byline span").forEach(function (s) {
      const txt = s.textContent.trim();
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
    const eyebrow = document.querySelector(".nb-eyebrow");
    if (!eyebrow || !meta.series || eyebrow.querySelector("a")) return;
    const wrap = document.createElement("a");
    wrap.href = ROOT + "series/" + meta.series + "/";
    while (eyebrow.firstChild) wrap.appendChild(eyebrow.firstChild);
    eyebrow.appendChild(wrap);
  }

  /* citations: tap opens a source sheet; sources gain ↩ backrefs */
  let veil = null;
  function closeSheet() {
    if (veil) {
      veil.remove();
      veil = null;
    }
    const s = document.querySelector(".nb-sheet");
    if (s) s.remove();
  }

  function citationContext(citation) {
    const locator = citation.getAttribute("data-nb-locator");
    const note = citation.getAttribute("data-nb-note");
    const url = citation.getAttribute("data-nb-url");
    if (!locator && !note && !url) return null;
    const context = document.createElement("div");
    context.className = "nb-sheet-context";
    if (locator) {
      const location = document.createElement("div");
      location.className = "nb-sheet-locator";
      location.textContent = locator;
      context.appendChild(location);
    }
    if (note) {
      const explanation = document.createElement("p");
      explanation.textContent = note;
      context.appendChild(explanation);
    }
    if (url) {
      const direct = document.createElement("a");
      direct.href = url;
      direct.target = "_blank";
      direct.rel = "noopener";
      direct.textContent = "Open cited passage";
      context.appendChild(direct);
    }
    return context;
  }

  function openSheet(num, li, citation) {
    closeSheet();
    veil = document.createElement("div");
    veil.className = "nb-veil";
    veil.addEventListener("click", closeSheet);
    const body = li.cloneNode(true);
    body.querySelectorAll(".nb-backref").forEach(function (b) {
      b.remove();
    });
    body.querySelectorAll("a").forEach(function (a) {
      a.target = "_blank";
      a.rel = "noopener";
    });
    const sheet = document.createElement("div");
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
    const context = citationContext(citation);
    if (context) sheet.querySelector(".nb-sheet-body").appendChild(context);
  }

  function normalizeSources() {
    document.querySelectorAll(".nb-sources li").forEach(function (li) {
      const a = li.querySelector("a[data-nb-source]");
      if (!a || a.textContent.trim().toLowerCase() !== "link") return;
      const parts = [];
      let node = li.firstChild;
      while (node && node !== a) {
        parts.push(node.textContent);
        const next = node.nextSibling;
        li.removeChild(node);
        node = next;
      }
      const title = parts
        .join("")
        .replace(/[.\s]+$/, "")
        .trim();
      if (title) a.textContent = title;
    });
  }

  function bindCitations() {
    const firstCiter = {};
    document.querySelectorAll("sup.nb-cite a").forEach(function (a, i) {
      const target = (a.getAttribute("href") || "").slice(1);
      if (!target) return;
      if (!a.id) a.id = "cite-" + target + (firstCiter[target] ? "-" + i : "");
      if (!firstCiter[target]) firstCiter[target] = a.id;
      a.addEventListener("click", function (e) {
        const li = document.getElementById(target);
        if (!li) return;
        e.preventDefault();
        openSheet(a.textContent.trim(), li, a);
      });
    });
    Object.keys(firstCiter).forEach(function (target) {
      const li = document.getElementById(target);
      if (!li || li.querySelector(".nb-backref")) return;
      const back = document.createElement("a");
      back.className = "nb-backref";
      back.href = "#" + firstCiter[target];
      back.textContent = "^";
      back.setAttribute("aria-label", "back to text");
      li.appendChild(document.createTextNode(" "));
      li.appendChild(back);
    });
    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape") closeSheet();
    });
  }

  /* last/next within the series, at the end of every article: sequences
     walk their lesson order, everything else walks the dates. Only what
     the catalog holds can render, and the catalog only ever holds
     published articles, so a yet-unwritten next can never appear. */
  function compareArticleKeys(a, b) {
    const ka = (a.date || "") + " " + (a.slug || "");
    const kb = (b.date || "") + " " + (b.slug || "");
    if (ka < kb) return -1;
    if (ka > kb) return 1;
    return 0;
  }

  function seriesNeighbors(articles, meta) {
    const sibs = articles.filter(function (e) {
      return e.series === meta.series;
    });
    if (meta.mode === "sequence" && meta.order) {
      return {
        prev: sibs.find(function (e) {
          return e.order === meta.order - 1;
        }),
        next: sibs.find(function (e) {
          return e.order === meta.order + 1;
        }),
      };
    }
    sibs.sort(compareArticleKeys);
    const i = sibs.findIndex(function (e) {
      return e.slug === meta.slug;
    });
    if (i < 0) return { prev: null, next: null };
    return { prev: sibs[i - 1], next: sibs[i + 1] };
  }

  function seriesNavLink(e, side) {
    return (
      '<a href="' +
      articleUrl(e) +
      '"' +
      (side === "next" ? ' class="next"' : "") +
      '><span class="nb-endnav-label">' +
      (side === "next" ? "Next →" : "← Previous") +
      '</span><span class="nb-endnav-title">' +
      escHtml(e.title) +
      "</span></a>"
    );
  }

  function bindSeriesNav(meta) {
    catalog().then(function (cat) {
      if (!cat) return;
      const pair = seriesNeighbors(cat.articles || [], meta);
      if (!pair.prev && !pair.next) return;
      const nav = document.createElement("nav");
      nav.className = "nb-endnav";
      nav.innerHTML =
        '<div class="nb-endnav-row">' +
        (pair.prev ? seriesNavLink(pair.prev, "prev") : "<span></span>") +
        (pair.next ? seriesNavLink(pair.next, "next") : "") +
        "</div>";
      (document.querySelector("article") || document.body).appendChild(nav);
    });
  }

  /* ---------------------------------------------------------------- search */

  function fuzzy(needle, hay) {
    let i = 0;
    for (let j = 0; j < hay.length && i < needle.length; j++) {
      if (hay[j] === needle[i]) i++;
    }
    if (i < needle.length) return 0;
    /* tightest window from the end backwards → 1.0 means a contiguous run */
    let end = -1;
    let start = -1;
    i = needle.length - 1;
    for (let k = hay.length - 1; k >= 0 && i >= 0; k--) {
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
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  function scoreDoc(d, tokens) {
    /* one search over everything: titles, deks, series, tags, full text */
    let total = 0;
    for (let t = 0; t < tokens.length; t++) {
      const q = tokens[t];
      let s = 0;
      if (d.title.indexOf(q) >= 0) s = Math.max(s, 6);
      else s = Math.max(s, fuzzy(q, d.title) * 3);
      if (d.dek.indexOf(q) >= 0) s = Math.max(s, 3);
      if (d.series.indexOf(q) >= 0) s = Math.max(s, 4);
      else s = Math.max(s, fuzzy(q, d.series) * 2);
      if (d.tags && d.tags.indexOf(q) >= 0) s = Math.max(s, 4);
      if (d.text && d.text.indexOf(q) >= 0) s = Math.max(s, 2);
      if (s <= 0.34) return 0; /* every token must land somewhere */
      total += s;
    }
    return total;
  }

  function snippet(d, tokens) {
    for (let t = 0; t < tokens.length; t++) {
      const i = d.text.indexOf(tokens[t]);
      if (i >= 0) {
        const from = Math.max(0, i - 80);
        const raw =
          (from > 0 ? "…" : "") + (d.e.text || "").slice(from, i + 100) + "…";
        let safe = escHtml(raw);
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

  function formatTemplateName(name) {
    const text = String(name || "");
    return text.charAt(0).toUpperCase() + text.slice(1);
  }

  function resultRow(d, tokens) {
    const e = d.e;
    const series = e.series_name || e.series;
    const kicker = e.section ? e.section + " — " + series : series;
    const body =
      tokens.length && d.text ? snippet(d, tokens) : escHtml(e.dek || "");
    return (
      '<a class="nb-item" href="' +
      articleUrl(e) +
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
      escHtml(formatTemplateName(e.template)) +
      "</span></div></a>"
    );
  }

  function initSearch() {
    const input = document.getElementById("nb-q");
    const out = document.getElementById("nb-results");
    const count = document.getElementById("nb-count");
    if (!input || !out) return;
    let docs = [];

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
            series: (
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
      const p = new URLSearchParams(location.search);
      if (p.get("q")) {
        input.value = p.get("q");
        render();
      }
      input.focus();
    }

    function renderRecent() {
      /* empty query: the newest articles under month labels, not a dump */
      const recent = docs.slice(0, 20);
      if (count) count.textContent = "";
      let seen = null;
      out.innerHTML = recent
        .map(function (d) {
          const e = d.e;
          const month = (e.date || "").slice(0, 7);
          let label = "";
          if (month && month !== seen) {
            seen = month;
            const mm = MONTHS[parseInt(month.slice(5), 10) - 1] || month;
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

    function render() {
      const q = (input.value || "").trim().toLowerCase();
      const tokens = q ? q.split(/\s+/) : [];
      if (!tokens.length) return renderRecent();
      const hits = docs
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
          " article" +
          (docs.length === 1 ? "" : "s");
      }
      out.innerHTML =
        hits
          .map(function (h) {
            return resultRow(h.d, tokens);
          })
          .join("") ||
        '<div class="nb-results-count" style="padding:20px 0">No matches.</div>';
    }

    let timer = null;
    input.addEventListener("input", function () {
      clearTimeout(timer);
      timer = setTimeout(render, 90);
    });
  }

  /* ------------------------------------------------------------------ init */

  /* The chrome itself is in the HTML on every page, articles included: the
     builder splices it into the article copies. This only binds behaviour. */
  function bindChrome() {
    document.querySelectorAll(".nb-appearance").forEach(function (btn) {
      btn.addEventListener("click", cycleAppearance);
    });
    applyAppearance(hashMode() || getAppearance());
    const menu = document.querySelector(".nb-menu");
    if (menu) {
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

  /* paper template: long abstracts clamp behind an ellipsis; a tap expands.
     Progressive: no JS means the full abstract, clamped only when it
     actually overflows. */
  function bindAbstract() {
    const abs = document.querySelector(".nb-paper-abstract");
    if (!abs) return;
    abs.classList.add("nb-clamped");
    if (abs.scrollHeight <= abs.clientHeight + 4) {
      abs.classList.remove("nb-clamped");
      return;
    }
    abs.setAttribute("role", "button");
    abs.setAttribute("aria-expanded", "false");
    abs.setAttribute("tabindex", "0");
    const toggle = function () {
      const clamped = abs.classList.toggle("nb-clamped");
      abs.setAttribute("aria-expanded", String(!clamped));
    };
    abs.addEventListener("click", toggle);
    abs.addEventListener("keydown", function (e) {
      if (e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        toggle();
      }
    });
  }

  function init() {
    bindChrome();
    renderCharts();
    renderMath();
    highlightCode();
    dressTables();

    const meta = articleMeta();
    if (meta) {
      buildToc();
      normalizeByline();
      linkEyebrow(meta);
      normalizeSources();
      bindCitations();
      bindSeriesNav(meta);
      bindAbstract();
    }

    initSearch();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
