"""The fixtures every suite is built from.

The shape of a test here: build a valid article, derive a failure case by
mutating it, and assert the exact finding at the exact tier. Valid cases stay
block-clean. PR mode runs against a real throwaway git repository, so the
diff-shape rules face actual git output.
"""

import contextlib
import datetime as dt
import io
import json
import pathlib
import shutil
import subprocess
import sys
import tempfile
import types
from collections.abc import Callable

import check
import pytest
from findings import Findings
from press import (
    OPEN_YAML,
    REPO,
    TODAY,
    article,
    git,
    make_full_library,
    make_press,
)

DUTY = [sys.executable, str(REPO / "engine" / "duty.py")]
VALIDATE_CONFIG = [sys.executable, str(REPO / "engine" / "validate_config.py")]
CI_HELPERS = [sys.executable, str(REPO / "engine" / "ci_helpers.py")]


@pytest.fixture(scope="session")
def testrepo() -> str:
    """The fixture press. Never mutate it; clone it."""
    return make_press()


@pytest.fixture
def clone_testrepo(testrepo: str) -> Callable[..., str]:
    """clone_testrepo("press", "templates") -> a scratch repo with those subtrees."""

    def clone(*subs: str) -> str:
        tmp = tempfile.mkdtemp()
        for sub in subs:
            shutil.copytree(pathlib.Path(testrepo) / sub, pathlib.Path(tmp) / sub)
        return tmp

    return clone


@pytest.fixture
def make_library() -> Callable[[dict[str, list[str]]], str]:
    """make_library({"semiconductors": ["tsmc"]}) -> a library root of published slugs."""

    def library(published: dict[str, list[str]]) -> str:
        tmp = tempfile.mkdtemp()
        for series, slugs in published.items():
            d = pathlib.Path(tmp) / "library" / series
            d.mkdir(parents=True)
            for slug in slugs:
                (d / f"{slug}.html").write_text("<html></html>")
        return tmp

    return library


@pytest.fixture
def run_local(testrepo: str) -> Callable[..., Findings]:
    """Proof one article HTML string against a series, as local mode does."""

    def run(
        html_text: str,
        series: str,
        *,
        slug: str | None = None,
        library: str | None = None,
        repo: str | None = None,
        today: str = TODAY,
        pr_body: str | None = None,
    ) -> Findings:
        repo = repo or testrepo
        tmp = tempfile.mkdtemp()
        slug = slug or "micron"
        d = pathlib.Path(tmp) / "library" / series
        d.mkdir(parents=True)
        article_path = d / f"{slug}.html"
        article_path.write_text(html_text)
        rep = check.Report()
        cfg, _ = check.load_series(repo, series)
        rep.strict = bool(cfg and cfg.get("strict"))
        body_meta = None
        if pr_body is not None:
            body_file = pathlib.Path(tmp) / "prbody.txt"
            body_file.write_text(pr_body)
            body_meta = check.resolve_pr_body(str(body_file), rep)
        check.check_article(
            str(article_path),
            series,
            repo=repo,
            library_dir=library,
            rep=rep,
            pr_body_meta=body_meta,
            today=dt.date.fromisoformat(today),
        )
        return Findings(rep)

    return run


@pytest.fixture
def run_main_json() -> Callable[[list[str]], dict]:
    """Drive check.py's CLI in-process and read back its --json report."""

    def run(argv: list[str]) -> dict:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            check.main(argv)
        return json.loads(buf.getvalue())

    return run


@pytest.fixture
def patched_repo(clone_testrepo: Callable[..., str]) -> Callable[..., str]:
    """A press whose series.yaml has `patch` appended to it."""

    def patch_repo(patch: str, series: str = "semiconductors") -> str:
        tmp = clone_testrepo("press", "templates", "engine")
        y = pathlib.Path(tmp) / "press" / "series" / series / "series.yaml"
        y.write_text(y.read_text() + patch)
        return tmp

    return patch_repo


@pytest.fixture
def overwrite_series(patched_repo: Callable[..., str]) -> Callable[..., str]:
    """A press with one series.yaml replaced wholesale, shapes validate_config would refuse included."""

    def overwrite(body: str, series: str = "ai-briefs") -> str:
        tmp = patched_repo("", series=series)
        y = pathlib.Path(tmp) / "press" / "series" / series / "series.yaml"
        y.write_text(body)
        return tmp

    return overwrite


@pytest.fixture
def seq_repo(clone_testrepo: Callable[..., str]) -> Callable[[], str]:
    """The semiconductors collection, reopened as a sequence."""

    def sequence() -> str:
        tmp = clone_testrepo("press", "templates")
        y = pathlib.Path(tmp) / "press" / "series" / "semiconductors" / "series.yaml"
        y.write_text(y.read_text().replace("mode: collection", "mode: sequence"))
        return tmp

    return sequence


@pytest.fixture
def open_press(clone_testrepo: Callable[..., str]) -> Callable[..., str]:
    """A press carrying a `wildcard` open series. Pass a series.yaml to vary it."""

    def press(series_yaml: str = OPEN_YAML) -> str:
        tmp = clone_testrepo("press", "templates", "engine")
        d = pathlib.Path(tmp) / "press" / "series" / "wildcard"
        d.mkdir()
        (d / "series.yaml").write_text(series_yaml)
        (d / "prompt.md").write_text("Anything about the AI stack.\n")
        return tmp

    return press


@pytest.fixture
def vc_output() -> Callable[[str], subprocess.CompletedProcess[str]]:
    """validate_config against a press: returncode, stdout, stderr."""

    def run(repo: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [*VALIDATE_CONFIG, "--repo", str(repo)], capture_output=True, text=True
        )

    return run


@pytest.fixture
def vc_rc(
    vc_output: Callable[[str], subprocess.CompletedProcess[str]],
) -> Callable[[str], int]:
    """0 when the press validates, 1 when it does not."""

    def rc(repo: str) -> int:
        return vc_output(repo).returncode

    return rc


@pytest.fixture
def run_duty() -> Callable[..., subprocess.CompletedProcess[str]]:
    """duty.py as the night shift invokes it, warts and exit codes included."""

    def run(*args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run([*DUTY, *args], capture_output=True, text=True)

    return run


@pytest.fixture
def duty(
    run_duty: Callable[..., subprocess.CompletedProcess[str]],
) -> Callable[..., dict]:
    """Tonight's work list, parsed. Use run_duty when the exit code is the point."""

    def work_list(repo: str, library: str, *, date: str = TODAY) -> dict:
        out = run_duty("--repo", str(repo), "--library", str(library), "--date", date)
        return json.loads(out.stdout)

    return work_list


@pytest.fixture
def ci_helper() -> Callable[[str, str], str]:
    """ci_helper("autopublish", "autopublish: true\\n") -> what the workflow reads."""

    def helper(cmd: str, series_yaml: str) -> str:
        repo = tempfile.mkdtemp()
        sd = pathlib.Path(repo) / "press" / "series" / "foo"
        sd.mkdir(parents=True)
        (sd / "series.yaml").write_text(series_yaml)
        git("init", "-q", "-b", "main", cwd=repo)
        git("config", "user.email", "t@t", cwd=repo)
        git("config", "user.name", "t", cwd=repo)
        git("add", "-A", cwd=repo)
        git("commit", "-qm", "config", cwd=repo)
        git("checkout", "-qb", "night", cwd=repo)
        lib = pathlib.Path(repo) / "library" / "foo"
        lib.mkdir(parents=True)
        (lib / "story.html").write_text("<html></html>")
        git("add", "-A", cwd=repo)
        git("commit", "-qm", "nb: foo/story", cwd=repo)
        # ci_helpers reads the diff from the current working directory (check.yml
        # runs it inside the checkout), so drive it with cwd set to the repo.
        return subprocess.run(
            [*CI_HELPERS, cmd, "--repo", repo, "--diff-base", "main"],
            cwd=repo,
            capture_output=True,
            text=True,
        ).stdout.strip()

    return helper


PR_BODY = """Nightly article.

```nb-meta
series: semiconductors
slug: micron
mode: collection
template: article
date: "2026-07-06"
title: "Micron Technology: The Scarcest Commodity in AI"
order: null
```
"""


class PressRepo:
    """A real git press: main carries the engine, library carries what shipped.

    The night shift's branch (claude/night-run) already adds one article. Drive
    it further with write/commit/checkout, then run_pr() to proof the PR as
    check.yml does.
    """

    def __init__(self, path: str, scratch: pathlib.Path) -> None:
        self.path = path
        self._scratch = scratch
        self.body = self.body_file(PR_BODY)

    def git(self, *args: str) -> None:
        git(*args, cwd=self.path)

    def write(self, relpath: str, text: str) -> pathlib.Path:
        p = pathlib.Path(self.path, relpath)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text)
        return p

    def commit(self, message: str) -> None:
        self.git("add", "-A")
        self.git("commit", "-qm", message)

    def checkout(self, branch: str, *, new: bool = False) -> None:
        self.git("checkout", "-qb" if new else "-q", branch)

    def body_file(self, text: str) -> str:
        """A PR body written outside the worktree, so it never joins the diff."""
        p = self._scratch / f"prbody-{len(list(self._scratch.iterdir()))}.txt"
        p.write_text(text)
        return str(p)

    def run_pr(
        self,
        *,
        pr_body: str | None = None,
        base: str = "library",
        head: str = "claude/night-run",
        library: str | None = None,
        today: str = TODAY,
        deletions_by_owner: bool = False,
    ) -> Findings:
        rep = check.Report()
        args = types.SimpleNamespace(
            repo=self.path,
            main=None,
            base=base,
            head=head,
            pr_body=pr_body,
            library=library,
            today=today,
            check_links=False,
            deletions_by_owner=deletions_by_owner,
        )
        check.run_pr_mode(args, rep)
        return Findings(rep)


@pytest.fixture
def pr_repo(clone_testrepo: Callable[..., str]) -> PressRepo:
    path = clone_testrepo("press", "templates")
    shutil.copytree(
        REPO / "engine",
        pathlib.Path(path) / "engine",
        ignore=shutil.ignore_patterns("__pycache__"),
    )
    repo = PressRepo(path, pathlib.Path(tempfile.mkdtemp()))
    repo.git("init", "-q", "-b", "main")
    repo.git("config", "user.email", "t@t")
    repo.git("config", "user.name", "t")
    repo.commit("engine")
    repo.checkout("library", new=True)
    repo.write("library/.gitkeep", "")
    repo.commit("library init")
    repo.checkout("claude/night-run", new=True)
    repo.write("library/semiconductors/micron.html", article())
    repo.commit("nb: semiconductors/micron")
    return repo


@pytest.fixture
def full_library() -> str:
    """A published library the builder can build a site from."""
    return make_full_library()


@pytest.fixture
def out_dir() -> Callable[[], str]:
    """A fresh empty directory to build a site into."""
    return tempfile.mkdtemp
