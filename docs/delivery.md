# Delivery: feeds, email, and the catalog API

## Feeds (zero setup)

Every paper publishes Atom feeds:

- `https://<you>.github.io/<repo>/feed.xml` for the whole paper
- `https://<you>.github.io/<repo>/series/<id>/feed.xml` for one series

The newest entries embed the full article content, so feed readers get the
whole article, not a teaser. Subscribe in any reader, or recreate morning
email delivery with an RSS-to-email service. No secrets, no configuration
in the repo.

## The morning email (opt-in)

The press builds an inline-styled email digest of every night's build:
headline, dek, and reading time per article, plus a total. The paperboy
workflow (`morning-mail.yml`) delivers the latest digest once per day.

Enable it with two steps.

1. Pick a send hour in `press/site.yaml`:

   ```yaml
   email:
     send_utc_hour: 12 # 12:00 UTC is 8am ET / 5am PT
   ```

2. Add repo Actions secrets (Settings, Secrets and variables, Actions):

| Secret               | Example                                           |
| -------------------- | ------------------------------------------------- |
| `MAIL_TO`            | `you@example.com`                                 |
| `MAIL_FROM`          | `The Nightly Build <you@gmail.com>`               |
| `MAIL_SMTP_SERVER`   | `smtp.gmail.com`                                  |
| `MAIL_SMTP_PORT`     | `465`                                             |
| `MAIL_SMTP_USERNAME` | `you@gmail.com`                                   |
| `MAIL_SMTP_PASSWORD` | a Gmail App Password, or your provider's SMTP key |

Without both the config block and `MAIL_TO`, the workflow gates itself off
silently. On mornings with no fresh build it asks `engine/duty.py` whether
last night was quiet by design (a cadence gap, a completed or paused paper)
or a missed night. Quiet by design sends nothing. A missed night sends a
short notice, for up to 14 days, so a broken schedule never fails silently.

Test a send anytime by running the workflow manually from the Actions tab.
`workflow_dispatch` bypasses the hour and freshness gates, not the secrets
gate. Credentials live only in GitHub Actions secrets, never in the repo,
and never anywhere the desk's untrusted-PR validation can see them.

Every night's digest is also archived at `builds/<date>/email.html` on the
site.

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
