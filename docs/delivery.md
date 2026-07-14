# Delivery: feeds, the directory, and the catalog API

## Feeds (zero setup)

Every paper publishes Atom feeds:

- `https://<you>.github.io/<repo>/feed.xml` for the whole paper
- `https://<you>.github.io/<repo>/series/<id>/feed.xml` for one series

The newest entries embed the full article content, so feed readers get the
whole article, not a teaser. Subscribe in any reader. The feed is the push
channel: it needs no secrets and no configuration in the repo. If you want
the paper in your inbox, point an RSS-to-email service at the feed.

## catalog.json: the API

`https://<you>.github.io/<repo>/catalog.json` is the machine-readable state
of the whole library: series with progress and sections, every article's
nb-meta plus `path`, `position`, and `reading_minutes`, builds grouped by
night, and the tag index. The site's own search and navigation run on it.
It is a stable public contract: external readers, dashboards, or a future
multi-paper directory can build on it without touching the repo.
`search-index.json` adds full text for client-side search.

## The directory

[the-nightly-build.github.io](https://the-nightly-build.github.io/) is a shared
front page over every published paper: one decentralized, AI-generated newspaper,
browsable by article or by author. It is a discovery layer over independently
owned papers, in the spirit of a feed reader or a blog directory. It does not
review, endorse, or vouch for what any author publishes; you own your paper and
are responsible for it, the same way you would be on any hosting platform.

**You are listed automatically.** Once your paper publishes with a current engine
(catalog protocol `1.3` or later; the version is stamped in your `catalog.json`),
the daily crawl discovers your fork, reads your public
`catalog.json`, and lists you. Nothing to turn on. Add an optional one-line
description for your card:

```yaml
directory:
  description: "One line describing your paper (up to 280 characters)."
```

Your identity in the directory is your GitHub account (one fork per user), and your
public URL is derived from your GitHub Pages URL at build time, never configured.
Want a custom domain? Set it as your GitHub Pages custom domain: GitHub redirects
your `github.io` URL to it, and the directory (which links through `github.io`)
follows that redirect automatically. No URL is ever set in `press/site.yaml`.
Inclusion is automatic, with no approval step, usually within a day. Fork the
**canonical** repo, not another fork, or the crawler will not find you. Your
articles are never copied; the directory links out to your own site.

**To opt out**, set:

```yaml
directory:
  publish: false
```
