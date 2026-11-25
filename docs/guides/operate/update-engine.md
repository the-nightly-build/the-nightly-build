# Update the engine

Upstream updates modify engine files on `main` and leave `press/` and `library`
untouched.

## Update from GitHub

Click **Sync fork** on your repository's GitHub page. The next scheduled run
starts with `nb sync`, validates your press against the updated engine (naming
any retired keys or moved templates), and opens an auto-merging workflow-sync PR
to `library` if protected workflows changed.

If any series uses a template moved to `examples/templates/`, copy it into
`press/templates/<id>/` before syncing.

## Update from a local checkout

From a clean checkout on `main`:

```sh
./nb sync --update-main-from-upstream
```

This fetches upstream, merges it into `main`, pushes, and syncs `library`
workflows. (Without `--update-main-from-upstream`, `nb sync` only tracks
`origin/main`.) Any merge conflict stops before touching `library`.

## After updating

- Compare your external scheduler prompt with the canonical prompt in
  [Schedule publication](schedule.md), since Git merges cannot update hosted
  schedules.
- Optionally dispatch `publish.yml` to rebuild the back catalog right away.

Never merge `library` into `main`, rerun `./nb setup` as an update, or edit
protected workflow copies directly on `library`.
