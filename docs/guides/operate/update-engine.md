# Update the engine

Your press and the engine have separate ownership. A normal upstream update
changes engine-owned files on `main` and leaves both `press/` and `library`
alone.

From GitHub, use **Sync fork**. The next scheduled run starts with `nb sync` and
repairs protected publishing workflows through their own CI-gated PR when
needed. An exact sync PR merges automatically once validated. The sync also
validates the press against the updated engine, so a key the engine retired
surfaces immediately instead of changing publication behavior silently.

From a clean local checkout, the complete update is:

```sh
./nb sync --update-main-from-upstream
```

The explicit flag fetches upstream, merges it into the fork's current `main`,
pushes, and synchronizes the `library` workflows. Without it, `nb sync` follows
only the fork's `origin/main`. A merge conflict stops before `library` changes.

After an update, compare the external scheduler prompt with the canonical prompt
in [Schedule](schedule.md). The schedule lives outside Git and cannot be updated
by a merge. You may also dispatch the publish workflow to rebuild the back
catalog immediately.

Never merge `library` into `main`, rerun setup as an update mechanism, or edit
protected workflow copies directly on `library`.
