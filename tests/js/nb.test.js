/*
 * Behavior tests for the browser runtime (engine/assets/nb.js).
 *
 * The rest of the suite is Python and never executes nb.js, so its DOM sinks,
 * search, and URL resolution were unverified — the blind spot that let the
 * finding-1.6 XSS ship. These drive the real source inside a jsdom window.
 *
 * jsdom gaps we polyfill (not behavior under test): window.matchMedia and
 * window.fetch. Chart.js is never loaded (it is a CDN script that cannot run in
 * jsdom); we stub window.Chart to observe the declarative-spec mapping and the
 * malformed-spec guard without touching a real canvas.
 */
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { JSDOM } from "jsdom";

const NB_SOURCE = readFileSync(
  new URL("../../engine/assets/nb.js", import.meta.url),
  "utf8",
);

const DEFAULT_SCRIPT_SRC = "http://ex.com/assets/nb.js";

/* A fetch stub routing nb.js's two data loads to supplied fixtures. */
function fetchRouter({ catalog = null, searchIndex = [] } = {}) {
  return (url) => {
    const u = String(url);
    if (u.includes("catalog.json")) {
      return Promise.resolve({
        ok: catalog !== null,
        json: () => Promise.resolve(catalog),
      });
    }
    if (u.includes("search-index.json")) {
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve(searchIndex),
      });
    }
    return Promise.resolve({ ok: false, json: () => Promise.resolve(null) });
  };
}

/* Load and run nb.js in a fresh jsdom window, then let its async work settle.
 * scriptSrc becomes document.currentScript.src, which is how nb.js derives ROOT. */
async function loadNb(
  html,
  { url = "http://ex.com/a.html", scriptSrc = DEFAULT_SCRIPT_SRC, fetch } = {},
) {
  const dom = new JSDOM(html, {
    url,
    runScripts: "dangerously",
    pretendToBeVisual: true,
  });
  const w = dom.window;
  w.matchMedia = () => ({
    matches: false,
    addListener() {},
    addEventListener() {},
  });
  w.fetch = fetch || fetchRouter();
  const script = w.document.createElement("script");
  Object.defineProperty(script, "src", { get: () => scriptSrc });
  script.textContent = NB_SOURCE;
  w.document.body.appendChild(script);
  await settle(w);
  return w;
}

/* Flush microtasks/timers so catalog(), fetch, and the search debounce resolve. */
function settle(window, ms = 40) {
  return new Promise((resolve) => window.setTimeout(resolve, ms));
}

function articlePage(
  bodyInner,
  meta = { series: "s", mode: "rolling", date: "2026-07-10" },
) {
  return (
    "<!doctype html><html><body>" +
    `<script id="nb-meta" type="application/json">${JSON.stringify(meta)}</script>` +
    bodyInner +
    '<input id="nb-q"><div id="nb-count"></div><div id="nb-results"></div>' +
    "</body></html>"
  );
}

/* A payload that is inert escaped text in article source (so the proof's text
 * sandbox passes it) but decodes to live markup once innerHTML re-parses it. */
const ESCAPED_IMG = "&lt;img src=x onerror=window.__pwned=1&gt;";
const DECODED_IMG = "<img src=x onerror=window.__pwned=1>";

test("buildToc renders a hostile heading and a hostile section id as inert text", async () => {
  const sections =
    '<section data-nb-section="a" id="&#34;&gt;&lt;img src=x onerror=window.__pwned=1&gt;"><h2>Intro</h2></section>' +
    `<section data-nb-section="b"><h2>Body ${ESCAPED_IMG}</h2></section>` +
    '<section data-nb-section="c"><h2>End</h2></section>';
  const html = articlePage(
    `<p class="nb-byline"><span>2026-07-10</span></p><article>${sections}</article>`,
  );
  const w = await loadNb(html, {
    fetch: fetchRouter({ catalog: { site_title: "T", articles: [] } }),
  });

  const toc = w.document.querySelector("details.nb-toc");
  assert.ok(toc, "toc renders for >=3 sections");
  assert.equal(
    toc.querySelectorAll("img").length,
    0,
    "no live <img> materializes from heading or id",
  );
  assert.equal(w.__pwned, undefined, "onerror handler never fires");
  const labels = [...toc.querySelectorAll("li a")].map((a) => a.textContent);
  assert.equal(labels.length, 3);
  assert.ok(
    labels.includes(`Body ${DECODED_IMG}`),
    "payload survives as visible text",
  );
});

test("buildToc lists sections led by any heading level and nests the deeper ones", async () => {
  const sections =
    '<section data-nb-section="orientation"><h2>Orientation</h2></section>' +
    '<section data-nb-section="for-x"><h3>The case for X</h3></section>' +
    '<section data-nb-section="for-y"><h3>The case for Y</h3></section>' +
    '<section data-nb-section="crux"><h2>Crux</h2></section>';
  const html = articlePage(
    `<p class="nb-byline"><span>2026-07-10</span></p><article>${sections}</article>`,
  );
  const w = await loadNb(html, {
    fetch: fetchRouter({ catalog: { site_title: "T", articles: [] } }),
  });

  const toc = w.document.querySelector("details.nb-toc");
  const labels = [...toc.querySelectorAll("li a")].map((a) => a.textContent);
  assert.deepEqual(labels, [
    "Orientation",
    "The case for X",
    "The case for Y",
    "Crux",
  ]);

  const top = toc.querySelector("ol");
  assert.deepEqual(
    [...top.children].map((li) => li.querySelector("a").textContent),
    ["Orientation", "Crux"],
    "h2 sections are top level",
  );
  const nested = top.querySelectorAll(":scope > li > ol > li > a");
  assert.deepEqual(
    [...nested].map((a) => a.textContent),
    ["The case for X", "The case for Y"],
    "the h3 sides nest under the h2 above them",
  );
  assert.equal(
    nested[0].getAttribute("href"),
    "#nb-for-x",
    "sections without an id get one and the link points at it",
  );
});

test("bindSequenceNav renders a hostile catalog neighbor title as inert text", async () => {
  const html = articlePage("<article><h1>Two</h1></article>", {
    series: "s",
    mode: "sequence",
    order: 2,
  });
  const catalog = {
    site_title: "T",
    articles: [
      {
        series: "s",
        order: 1,
        title: `Prev ${DECODED_IMG}`,
        path: "/library/p.html",
      },
      { series: "s", order: 3, title: "Next", path: "/library/n.html" },
    ],
  };
  const w = await loadNb(html, { fetch: fetchRouter({ catalog }) });

  const nav = w.document.querySelector("nav.nb-endnav");
  assert.ok(nav, "end-nav renders when neighbors exist");
  assert.equal(
    nav.querySelectorAll("img").length,
    0,
    "no live <img> from a hostile title",
  );
  assert.equal(w.__pwned, undefined);
  assert.ok(
    nav.textContent.includes("onerror"),
    "payload survives as visible text",
  );
});

test("search filters to matching entries and reports the count", async () => {
  const searchIndex = [
    {
      title: "Alpha",
      slug: "alpha",
      path: "/library/alpha.html",
      dek: "first",
      template: "brief",
    },
    {
      title: "Beta",
      slug: "beta",
      path: "/library/beta.html",
      dek: "second",
      template: "brief",
    },
    {
      title: "Gamma",
      slug: "gamma",
      path: "/library/gamma.html",
      dek: "third",
      template: "brief",
    },
  ];
  const w = await loadNb(articlePage("<article></article>"), {
    fetch: fetchRouter({ searchIndex }),
  });

  const input = w.document.getElementById("nb-q");
  input.value = "beta";
  input.dispatchEvent(new w.Event("input"));
  await settle(w, 150);

  const items = w.document.querySelectorAll("#nb-results a.nb-item");
  assert.equal(items.length, 1, "only the matching entry is shown");
  assert.equal(items[0].querySelector("h3").textContent, "Beta");
  assert.match(
    w.document.getElementById("nb-count").textContent,
    /1 of 3 articles/,
  );
});

test("search escapes a hostile title and builds a highlighted snippet", async () => {
  const searchIndex = [
    {
      title: `Danger ${DECODED_IMG}`,
      slug: "danger",
      path: "/library/danger.html",
      dek: "a dek",
      text: "the quick breach fox jumps over the lazy dog",
      template: "lesson",
    },
  ];
  const w = await loadNb(articlePage("<article></article>"), {
    fetch: fetchRouter({ searchIndex }),
  });

  const input = w.document.getElementById("nb-q");
  input.value = "breach";
  input.dispatchEvent(new w.Event("input"));
  await settle(w, 150);

  const item = w.document.querySelector("#nb-results a.nb-item");
  assert.ok(item, "hostile entry still matches");
  assert.equal(item.querySelectorAll("img").length, 0, "title renders inert");
  const mark = item.querySelector(".nb-snippet mark");
  assert.ok(mark, "the matched token is highlighted");
  assert.equal(mark.textContent.toLowerCase(), "breach");
});

test("ROOT is derived from the script URL so article links resolve under a subpath site", async () => {
  const searchIndex = [
    {
      title: "Alpha",
      slug: "alpha",
      path: "/library/2026/a.html",
      template: "brief",
      dek: "d",
    },
  ];
  const w = await loadNb(articlePage("<article></article>"), {
    url: "http://ex.com/repo/search/",
    scriptSrc: "http://ex.com/repo/assets/nb.js",
    fetch: fetchRouter({ searchIndex }),
  });

  const input = w.document.getElementById("nb-q");
  input.value = "alpha";
  input.dispatchEvent(new w.Event("input"));
  await settle(w, 150);

  const href = w.document
    .querySelector("#nb-results a.nb-item")
    .getAttribute("href");
  assert.equal(
    href,
    "http://ex.com/repo/library/2026/a.html",
    "link resolves under /repo/, not the page dir",
  );
});

test("legacy shelf charts still map a declarative spec into Chart config and skip a malformed spec", async () => {
  const html =
    "<!doctype html><html><body>" +
    '<figure><script type="application/json" data-nb-chart>' +
    '{"type":"bar","labels":["x","y"],"series":[{"name":"s","values":[1,2]}]}' +
    "</script><canvas></canvas></figure>" +
    '<figure><script type="application/json" data-nb-chart>{ this is not json</script><canvas></canvas></figure>' +
    "</body></html>";
  const dom = new JSDOM(html, {
    url: "http://ex.com/a.html",
    runScripts: "dangerously",
    pretendToBeVisual: true,
  });
  const w = dom.window;
  w.matchMedia = () => ({
    matches: false,
    addListener() {},
    addEventListener() {},
  });
  w.fetch = fetchRouter();
  const recorded = [];
  w.Chart = function Chart(canvas, config) {
    recorded.push(config);
    this.destroy = () => {};
  };
  const script = w.document.createElement("script");
  Object.defineProperty(script, "src", { get: () => DEFAULT_SCRIPT_SRC });
  script.textContent = NB_SOURCE;
  w.document.body.appendChild(script);
  await settle(w);

  assert.equal(
    recorded.length,
    1,
    "only the well-formed spec renders; the malformed one is skipped",
  );
  assert.equal(recorded[0].type, "bar");
  // Cross-realm arrays (jsdom's Array !== node's) fail deepStrictEqual; compare by value.
  assert.equal(
    JSON.stringify(recorded[0].data.labels),
    JSON.stringify(["x", "y"]),
  );
  assert.equal(
    JSON.stringify(recorded[0].data.datasets[0].data),
    JSON.stringify([1, 2]),
  );
});

test("citation sheet adds the clicked marker's locator, note, and direct target", async () => {
  const html = articlePage(
    '<article><p>One<sup class="nb-cite"><a href="#s1" data-nb-locator="Fig. 3 · p. 6" data-nb-url="https://example.org/paper.pdf#page=6" data-nb-note="The IsoFLOP minima behind the frontier.">1</a></sup></p>' +
      '<p>Two<sup class="nb-cite"><a href="#s1" data-nb-locator="Appendix G · p. 29" data-nb-note="The optimizer control.">1</a></sup></p></article>' +
      '<section class="nb-sources"><ol><li id="s1"><a data-nb-source href="https://example.org/paper">The paper</a></li></ol></section>',
  );
  const w = await loadNb(html);
  const citations = w.document.querySelectorAll("sup.nb-cite a");

  citations[0].dispatchEvent(new w.MouseEvent("click", { bubbles: true }));
  assert.match(
    w.document.querySelector(".nb-sheet").textContent,
    /Fig. 3 · p. 6/,
  );
  assert.match(
    w.document.querySelector(".nb-sheet").textContent,
    /IsoFLOP minima/,
  );
  assert.equal(
    w.document.querySelector(".nb-sheet-context a").href,
    "https://example.org/paper.pdf#page=6",
  );

  citations[1].dispatchEvent(new w.MouseEvent("click", { bubbles: true }));
  assert.match(
    w.document.querySelector(".nb-sheet").textContent,
    /Appendix G · p. 29/,
  );
  assert.doesNotMatch(
    w.document.querySelector(".nb-sheet").textContent,
    /IsoFLOP minima/,
  );
});

/* ------------------------------------------------- math + code furniture */

const MATH_FIGURE =
  '<figure class="nb-math"><div class="nb-math-eq">\\varphi(x) = ax + bx^{3}</div></figure>' +
  '<p><span class="nb-math-in">O^{\\top} O = I</span></p>';

/* A KaTeX stub the page ships inline, standing in for window.katex. */
const KATEX_STUB =
  "<script>window.__mathCalls = [];" +
  "window.katex = { render: function (tex, el, opts) {" +
  "  window.__mathCalls.push({ tex: tex, display: opts.displayMode, trust: opts.trust });" +
  "  el.innerHTML = '<span class=\"katex\"></span>';" +
  "} };</script>";

test("math typesets display and inline TeX, trusting only \\htmlClass", async () => {
  const w = await loadNb(
    articlePage(KATEX_STUB + "<article>" + MATH_FIGURE + "</article>"),
  );

  const calls = w.__mathCalls;
  assert.equal(calls.length, 2);
  assert.equal(calls[0].tex, "\\varphi(x) = ax + bx^{3}");
  assert.equal(calls[0].display, true, "nb-math-eq renders in display mode");
  assert.equal(calls[1].display, false, "nb-math-in renders inline");
  assert.equal(calls[0].trust({ command: "\\htmlClass" }), true);
  assert.equal(calls[0].trust({ command: "\\href" }), false);
  assert.equal(
    w.document.querySelectorAll('script[src*="katex"]').length,
    0,
    "katex already present: nothing is fetched",
  );
});

test("math on a page without KaTeX loads the pinned engine copy; a page without math loads nothing", async () => {
  const w = await loadNb(articlePage("<article>" + MATH_FIGURE + "</article>"));
  const js = w.document.querySelector('script[src*="katex.min.js"]');
  const css = w.document.querySelector('link[href*="katex.min.css"]');
  assert.ok(js, "engine KaTeX script is appended");
  assert.ok(css, "engine KaTeX stylesheet is appended");
  assert.match(js.integrity, /^sha384-/, "script is SRI-pinned");
  assert.match(css.integrity, /^sha384-/, "stylesheet is SRI-pinned");
  assert.equal(js.crossOrigin, "anonymous");

  const bare = await loadNb(
    articlePage("<article><p>No math here.</p></article>"),
  );
  assert.equal(
    bare.document.querySelectorAll('script[src*="katex"]').length,
    0,
  );
  assert.equal(bare.document.querySelectorAll('link[href*="katex"]').length, 0);
});

test("a press-pinned KaTeX outranks the engine's and typesets once it lands", async () => {
  const html =
    "<!doctype html><html><head>" +
    '<script src="https://cdn.example/katex@9/katex.min.js" defer></script>' +
    "</head><body><article>" +
    MATH_FIGURE +
    "</body></html>";
  const w = await loadNb(html);
  assert.equal(
    w.document.querySelectorAll('script[src*="katex"]').length,
    1,
    "the press copy is the only KaTeX tag",
  );

  /* the deferred press script executes after nb.js: stub it, then land it */
  w.__mathCalls = [];
  w.katex = {
    render: (tex, el, opts) =>
      w.__mathCalls.push({ tex, display: opts.displayMode }),
  };
  const press = w.document.querySelector('script[src*="cdn.example"]');
  press.dispatchEvent(new w.Event("load"));
  await settle(w);
  assert.equal(w.__mathCalls.length, 2, "typeset ran against the press copy");
});

const CODE_FIGURE =
  '<figure class="nb-code"><div class="nb-code-head"><span class="nb-code-file">a.py</span><span>python</span></div>' +
  '<pre><code class="language-python">def f(x):\n    return x</code></pre></figure>';

test("a code listing loads pinned Prism components in order, then highlights", async () => {
  const w = await loadNb(articlePage("<article>" + CODE_FIGURE + "</article>"));
  assert.equal(w.Prism.manual, true, "Prism auto-highlight is off");

  /* components chain one at a time; land each load to advance the chain */
  const seen = [];
  const highlighted = [];
  w.Prism.highlightElement = (el) => highlighted.push(el);
  for (let i = 0; i < 4; i++) {
    const tags = [...w.document.querySelectorAll('script[src*="prism-"]')];
    assert.equal(tags.length, seen.length + 1, "one new component per load");
    const tag = tags[tags.length - 1];
    assert.match(tag.integrity, /^sha384-/, "component is SRI-pinned");
    seen.push(tag.src);
    tag.dispatchEvent(new w.Event("load"));
    await settle(w, 5);
  }
  assert.match(seen[0], /prism-core/);
  assert.match(seen[1], /prism-clike/);
  assert.match(seen[2], /prism-javascript/);
  assert.match(seen[3], /prism-python/);
  assert.equal(highlighted.length, 1, "the listing is highlighted once ready");
  assert.equal(highlighted[0].className, "language-python");
});

test("a press-pinned Prism is left to highlight on its own", async () => {
  const html =
    "<!doctype html><html><head>" +
    '<script src="https://cdn.example/prism/prism-core.min.js" defer></script>' +
    "</head><body><article>" +
    CODE_FIGURE +
    "</body></html>";
  const w = await loadNb(html);
  assert.equal(
    w.document.querySelectorAll('script[src*="prism-"]').length,
    1,
    "no engine components are fetched beside the press copy",
  );
  assert.equal(
    w.Prism,
    undefined,
    "the press copy's own bootstrap is untouched",
  );
});
