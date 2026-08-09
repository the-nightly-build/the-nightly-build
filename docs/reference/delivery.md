# Delivery: feeds, the directory, and the catalog API

## Feeds (zero setup)

Every paper publishes Atom feeds:

- `https://<you>.github.io/<repo>/feed.xml` for the whole paper
- `https://<you>.github.io/<repo>/series/<id>/feed.xml` for one series

The newest entries embed the full article content, so a feed reader shows the
whole article. The feed needs no secrets and no configuration in the repo. For
email delivery, point an RSS-to-email service at the feed.

## catalog.json: the API

`https://<you>.github.io/<repo>/catalog.json` is the machine-readable state of
the whole library: series with progress and sections, every article's nb-meta
plus `path`, `position`, and `reading_minutes`, builds grouped by night, and the
tag index. Generated pages and the catalog come from the same library state.
External readers and dashboards can use the catalog without touching the repo.
`search-index.json` carries full text for client-side search.

## The directory

[the-nightly-build.github.io](https://the-nightly-build.github.io/) is a shared
front page over every published paper: one decentralized, AI-generated
newspaper, browsable by article or by author. It is a discovery layer over
independently owned papers, in the spirit of a feed reader or a blog directory.
It does not review, endorse, or vouch for what any author publishes. You own
your paper and are responsible for it, the same way you would be on any hosting
platform.

**You are listed automatically.** Once your paper publishes with a current
engine (catalog protocol `1.3` or later, stamped in your `catalog.json`), the
daily crawl discovers your fork, reads your public `catalog.json`, and lists
you. Add an optional one-line description for your card:

```yaml
directory:
  description: "One line describing your paper (up to 280 characters)."
```

Your identity in the directory is your GitHub account (one fork per user), and
your public URL is derived from your GitHub Pages URL at build time, never
configured. For a custom domain, set it as your GitHub Pages custom domain.
GitHub redirects your `github.io` URL to it, and the directory, which links
through `github.io`, follows that redirect automatically. No URL is ever set in
`press/site.yaml`. Inclusion is automatic, with no approval step, usually within
a day. Fork the **canonical** repo, not another fork, or the crawler will not
find you. Your articles are never copied. The directory links out to your own
site.

**To opt out**, set:

```yaml
directory:
  publish: false
```
