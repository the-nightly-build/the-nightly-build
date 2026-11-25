# Delivery: feeds, the directory, and the catalog API

## Feeds (zero setup)

Every paper publishes Atom feeds with full recent article content embedded (no
secrets or repo config needed):

- Paper-wide: `https://<you>.github.io/<repo>/feed.xml`
- Per-series: `https://<you>.github.io/<repo>/series/<id>/feed.xml`

For email delivery, point any RSS-to-email service at a feed URL.

## catalog.json: the API

| Endpoint            | Contents                                                                                                                                          |
| ------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------- |
| `catalog.json`      | Machine-readable library state: series progress/sections, article `nb-meta`, `path`, `position`, `reading_minutes`, nightly builds, and tag index |
| `search-index.json` | Full article text for client-side search                                                                                                          |

Both live at `https://<you>.github.io/<repo>/` and are built from `library`
alongside the HTML pages. External readers and dashboards can query them without
touching the repository.

## The directory

[the-nightly-build.github.io](https://the-nightly-build.github.io/) is a
decentralized directory over independently owned papers, browsable by article or
author. It links out to your site without copying your articles or reviewing,
endorsing, or vouching for content. You own and remain responsible for your
paper.

- **Automatic listing:** once you publish from a fork of the **canonical**
  repository on catalog protocol `1.3` or later (stamped in `catalog.json`), the
  daily crawl discovers and lists your paper (one fork per GitHub account,
  usually within a day). Forking another fork will not be discovered.
- **Custom domains:** configure your custom domain in GitHub Pages settings
  only, never in `press/site.yaml`. GitHub redirects `github.io` to your custom
  domain, and the directory follows the redirect.

Add an optional card description or opt out in `press/site.yaml`:

```yaml
directory:
  description: "One line describing your paper (up to 280 characters)."
  publish: false # omit or set true to remain listed
```
