# Delivery: feeds, email, and the catalog API

## Feeds (zero setup)

Every press publishes Atom feeds:

- `https://<you>.github.io/<repo>/feed.xml` for the whole press
- `https://<you>.github.io/<repo>/series/<id>/feed.xml` for one series

The newest entries embed the full edition content, so feed readers get the
whole edition, not a teaser. Subscribe in any reader, or recreate morning
email delivery with an RSS-to-email service. No secrets, no configuration
in the repo.

## The morning email (opt-in)

The press builds an inline-styled email digest of every night's build:
headline, dek, and reading time per edition, plus a total. The paperboy
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
last night was quiet by design (a cadence gap, a completed or paused press)
or a missed night. Quiet by design sends nothing. A missed night sends a
short notice, for up to 14 days, so a broken schedule never fails silently.

Test a send anytime by running the workflow manually from the Actions tab.
`workflow_dispatch` bypasses the hour and freshness gates, not the secrets
gate. Credentials live only in GitHub Actions secrets, never in the repo,
and never anywhere the editor's untrusted-PR validation can see them.

Every night's digest is also archived at `builds/<date>/email.html` on the
site.

## catalog.json: the API

`https://<you>.github.io/<repo>/catalog.json` is the machine-readable state
of the whole library: series with progress and sections, every edition's
nb-meta plus `path`, `position`, and `reading_minutes`, builds grouped by
night, and the tag index. The site's own search and navigation run on it.
It is a stable public contract: external readers, dashboards, or a future
multi-press directory can build on it without touching the repo.
`search-index.json` adds full text for client-side search.

## Joining the network (opt-in)

The Nightly Build network is a discovery layer over independently owned presses,
in the spirit of a feed reader or a blog directory. It indexes presses that opt
in; it does not review, endorse, or vouch for what any press publishes. You own
your paper and are responsible for it, the same way you would be on any hosting
platform.

Opt in from `press/site.yaml`:

```yaml
network:
  publish: true
  description: "One line describing your press (up to 280 characters)."
```

`description` is the only field you write. Your public URL is derived from your
GitHub Pages URL at build time, never configured, so there is nothing to keep in
sync when you fork. Absent, or `publish: false`, keeps the press unlisted. When
you opt in, the next build adds a `network` block to `catalog.json` (protocol
`1.2`); the directory reads that block when it crawls. The directory site itself
is still being built, so opting in now simply means you are listed once it goes
live.
