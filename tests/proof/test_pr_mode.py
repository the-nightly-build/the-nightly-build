"""Exercise every diff shape accepted by Article PR validation.

Real Git branches cover one article bundle, owner-authorized retraction, and an
exact protected-workflow sync. The checks also prove that validation reads the
named head's committed blobs rather than a checkout or PR-body description.
"""

import pathlib

from conftest import PressRepo
from press import article, write_agent_artifacts


def prepare_revision(
    pr_repo: PressRepo,
    *,
    legacy: bool = False,
    paused: bool = False,
    prior_notes: int = 0,
) -> str:
    pr_repo.checkout("library")
    if paused:
        series = pathlib.Path(pr_repo.path, "press/series/semiconductors/series.yaml")
        series.write_text(series.read_text() + "paused: true\n")
    pr_repo.write("library/semiconductors/micron.html", article())
    if not legacy:
        write_agent_artifacts(pr_repo.path, "semiconductors", slug="micron")
    for number in range(1, prior_notes + 1):
        pr_repo.write(
            f"agent-artifacts/semiconductors/micron/revisions/{number:02d}.md",
            f"# Revision {number:02d}\n\nEarlier correction.\n",
        )
    pr_repo.commit("publish micron")
    pr_repo.checkout("owner/revise-micron", new=True)
    pr_repo.write(
        "library/semiconductors/micron.html",
        article().replace("</body>", "<!-- corrected -->\n</body>"),
    )
    pr_repo.write(
        f"agent-artifacts/semiconductors/micron/revisions/{prior_notes + 1:02d}.md",
        "# Revision\n\nCorrect a factual error in the published article.\n",
    )
    pr_repo.commit("revise micron")
    return "owner/revise-micron"


def test_pr_happy_path(pr_repo: PressRepo) -> None:
    result = pr_repo.run_pr()

    assert not result.blocks


def test_preflight_passes_from_the_library_checkout(pr_repo: PressRepo) -> None:
    """Proof reads proposed blobs even when the checkout lacks the new bundle.

    On 2026-07-16 two article runs hit a false file-not-found block because
    preflight ran from the library checkout. The named head, not the working
    tree, is the exact content a merge would publish.
    """
    pr_repo.checkout("library")

    result = pr_repo.run_pr()

    assert not result.blocks


def test_pr_proofs_the_head_ref_not_the_working_tree(pr_repo: PressRepo) -> None:
    pr_repo.write("library/semiconductors/micron.html", "uncommitted garbage")

    result = pr_repo.run_pr()

    assert not result.blocks


def test_pr_touching_two_files(pr_repo: PressRepo) -> None:
    pr_repo.write("library/semiconductors/extra.txt", "x")
    pr_repo.commit("extra")

    result = pr_repo.run_pr()

    assert "B-DIFF-SHAPE" in result.blocks


def test_pr_accepts_matching_figure_assets(pr_repo: PressRepo) -> None:
    pr_repo.write("library/semiconductors/micron/figure-1.png", "image")
    pr_repo.commit("figure asset")

    result = pr_repo.run_pr()

    assert "B-DIFF-SHAPE" not in result.codes


def test_pr_requires_the_complete_matching_artifact_tree(pr_repo: PressRepo) -> None:
    pr_repo.git(
        "rm",
        "-q",
        "agent-artifacts/semiconductors/micron/editor/01/editorial-review.md",
    )
    pr_repo.commit("drop editor review")

    result = pr_repo.run_pr()

    assert "B-AGENT-ARTIFACTS" in result.blocks


def test_pr_accepts_numbered_role_invocations(pr_repo: PressRepo) -> None:
    for filename in ("brief.md", "draft-handoff.md"):
        pr_repo.write(
            f"agent-artifacts/semiconductors/micron/writer/02/{filename}",
            f"# Writer revision\n\nComplete {filename}.\n",
        )
    pr_repo.commit("record writer revision")

    result = pr_repo.run_pr()

    assert "B-AGENT-ARTIFACTS" not in result.codes


def test_pr_accepts_an_article_revision_with_only_a_note(
    pr_repo: PressRepo,
) -> None:
    head = prepare_revision(pr_repo)

    result = pr_repo.run_pr(head=head)

    assert not result.blocks


def test_revision_of_a_legacy_article_starts_notes_at_01(
    pr_repo: PressRepo,
) -> None:
    head = prepare_revision(pr_repo, legacy=True)

    result = pr_repo.run_pr(head=head)

    assert not result.blocks


def test_revision_note_uses_the_next_sequence_number(pr_repo: PressRepo) -> None:
    head = prepare_revision(pr_repo, prior_notes=2)

    result = pr_repo.run_pr(head=head)

    assert not result.blocks


def test_revision_accepts_matching_asset_additions_modifications_and_deletions(
    pr_repo: PressRepo,
) -> None:
    pr_repo.checkout("library")
    pr_repo.write("library/semiconductors/micron.html", article())
    write_agent_artifacts(pr_repo.path, "semiconductors", slug="micron")
    pr_repo.write("library/semiconductors/micron/old.png", "old")
    pr_repo.write("library/semiconductors/micron/change.png", "before")
    pr_repo.commit("publish micron with assets")
    pr_repo.checkout("owner/revise-assets", new=True)
    pr_repo.write(
        "library/semiconductors/micron.html",
        article().replace("</body>", "<!-- assets revised -->\n</body>"),
    )
    pr_repo.git("rm", "-q", "library/semiconductors/micron/old.png")
    pr_repo.write("library/semiconductors/micron/change.png", "after")
    pr_repo.write("library/semiconductors/micron/new.png", "new")
    pr_repo.write(
        "agent-artifacts/semiconductors/micron/revisions/01.md",
        "# Asset revision\n\nReplace an inaccurate figure and its source data.\n",
    )
    pr_repo.commit("revise assets")

    result = pr_repo.run_pr(head="owner/revise-assets")

    assert not result.blocks


def test_revision_can_change_metadata_allowed_by_normal_proof(
    pr_repo: PressRepo,
) -> None:
    head = prepare_revision(pr_repo)
    revised = pathlib.Path(pr_repo.path, "library/semiconductors/micron.html")
    revised.write_text(
        revised.read_text().replace('"date": "2026-07-06"', '"date": "2026-07-05"')
    )
    pr_repo.commit("correct publication date")

    result = pr_repo.run_pr(head=head)

    assert not result.blocks


def test_revision_requires_a_note(pr_repo: PressRepo) -> None:
    head = prepare_revision(pr_repo)
    pr_repo.git(
        "rm",
        "-q",
        "agent-artifacts/semiconductors/micron/revisions/01.md",
    )
    pr_repo.commit("omit revision note")

    result = pr_repo.run_pr(head=head)

    assert "B-REVISION-NOTE" in result.blocks


def test_revision_rejects_multiple_notes(pr_repo: PressRepo) -> None:
    head = prepare_revision(pr_repo)
    pr_repo.write(
        "agent-artifacts/semiconductors/micron/revisions/02.md",
        "# Another note\n\nThis revision should have one explanation.\n",
    )
    pr_repo.commit("add two revision notes")

    result = pr_repo.run_pr(head=head)

    assert "B-REVISION-NOTE" in result.blocks


def test_revision_rejects_an_out_of_sequence_note(pr_repo: PressRepo) -> None:
    head = prepare_revision(pr_repo)
    pr_repo.git(
        "mv",
        "agent-artifacts/semiconductors/micron/revisions/01.md",
        "agent-artifacts/semiconductors/micron/revisions/02.md",
    )
    pr_repo.commit("skip revision note 01")

    result = pr_repo.run_pr(head=head)

    assert "B-REVISION-NOTE" in result.blocks


def test_revision_rejects_an_empty_note(pr_repo: PressRepo) -> None:
    head = prepare_revision(pr_repo)
    pr_repo.write("agent-artifacts/semiconductors/micron/revisions/01.md", "")
    pr_repo.commit("empty revision note")

    result = pr_repo.run_pr(head=head)

    assert "B-REVISION-NOTE" in result.blocks


def test_revision_rejects_a_symlinked_note(pr_repo: PressRepo) -> None:
    head = prepare_revision(pr_repo)
    note = pathlib.Path(
        pr_repo.path,
        "agent-artifacts/semiconductors/micron/revisions/01.md",
    )
    note.unlink()
    note.symlink_to("explanation.md")
    pr_repo.commit("symlink revision note")

    result = pr_repo.run_pr(head=head)

    assert "B-REVISION-NOTE" in result.blocks


def test_revision_rejects_committed_role_artifacts(pr_repo: PressRepo) -> None:
    head = prepare_revision(pr_repo)
    for filename in ("brief.md", "draft-handoff.md"):
        pr_repo.write(
            f"agent-artifacts/semiconductors/micron/writer/02/{filename}",
            f"# Writer revision\n\nComplete {filename}.\n",
        )
    pr_repo.commit("commit optional process artifacts")

    result = pr_repo.run_pr(head=head)

    assert "B-DIFF-SHAPE" in result.blocks


def test_revision_cannot_modify_published_artifacts(pr_repo: PressRepo) -> None:
    head = prepare_revision(pr_repo)
    review = pathlib.Path(
        pr_repo.path,
        "agent-artifacts/semiconductors/micron/editor/01/editorial-review.md",
    )
    review.write_text(review.read_text() + "Changed history.\n")
    pr_repo.commit("rewrite old review")

    result = pr_repo.run_pr(head=head)

    assert "B-DIFF-SHAPE" in result.blocks


def test_revision_cannot_modify_an_earlier_revision_note(
    pr_repo: PressRepo,
) -> None:
    head = prepare_revision(pr_repo, prior_notes=1)
    note = pathlib.Path(
        pr_repo.path,
        "agent-artifacts/semiconductors/micron/revisions/01.md",
    )
    note.write_text(note.read_text() + "Rewritten history.\n")
    pr_repo.commit("rewrite earlier revision note")

    result = pr_repo.run_pr(head=head)

    assert "B-DIFF-SHAPE" in result.blocks


def test_revision_rejects_a_note_for_another_article(pr_repo: PressRepo) -> None:
    head = prepare_revision(pr_repo)
    pr_repo.write(
        "agent-artifacts/semiconductors/tsmc/revisions/01.md",
        "# Wrong article\n\nThis note belongs somewhere else.\n",
    )
    pr_repo.commit("add unrelated revision note")

    result = pr_repo.run_pr(head=head)

    assert "B-DIFF-SHAPE" in result.blocks


def test_paused_series_can_receive_a_revision(pr_repo: PressRepo) -> None:
    head = prepare_revision(pr_repo, paused=True)

    result = pr_repo.run_pr(head=head)

    assert not result.blocks


def test_paused_series_still_blocks_a_new_article(pr_repo: PressRepo) -> None:
    pr_repo.checkout("library")
    series = pathlib.Path(pr_repo.path, "press/series/semiconductors/series.yaml")
    series.write_text(series.read_text() + "paused: true\n")
    pr_repo.commit("pause semiconductors")
    pr_repo.checkout("nb/paused-new-article", new=True)
    pr_repo.write(
        "library/semiconductors/tsmc.html",
        article().replace('"slug": "micron"', '"slug": "tsmc"'),
    )
    write_agent_artifacts(pr_repo.path, "semiconductors", slug="tsmc")
    pr_repo.commit("try paused publication")

    result = pr_repo.run_pr(head="nb/paused-new-article")

    assert "B-SERIES" in result.blocks


def test_pr_rejects_another_articles_figure_asset(pr_repo: PressRepo) -> None:
    pr_repo.write("library/semiconductors/tsmc/figure-1.png", "image")
    pr_repo.commit("wrong figure asset")

    result = pr_repo.run_pr()

    assert "B-DIFF-SHAPE" in result.blocks


def test_pr_modifying_engine_code(pr_repo: PressRepo) -> None:
    check_py = pathlib.Path(pr_repo.path, "engine", "check.py")
    pr_repo.write("engine/check.py", check_py.read_text() + "\n# sneak\n")
    pr_repo.commit("sneak")

    result = pr_repo.run_pr()

    assert "B-DIFF-SHAPE" in result.blocks


def prepare_workflow_sync(
    pr_repo: PressRepo,
    paths: tuple[str, ...] = (
        ".github/workflows/check.yml",
        ".github/workflows/publish.yml",
    ),
) -> str:
    workflows = {
        ".github/workflows/check.yml": "name: canonical check\n",
        ".github/workflows/publish.yml": "name: canonical publish\n",
    }
    pr_repo.checkout("library")
    pr_repo.checkout("nb/sync-library-workflows", new=True)
    for path in paths:
        pr_repo.write(path, workflows[path])
    pr_repo.commit("chore: sync library workflows from main abc123")
    return "nb/sync-library-workflows"


def test_pr_accepts_an_exact_workflow_sync(pr_repo: PressRepo) -> None:
    head = prepare_workflow_sync(pr_repo)

    result = pr_repo.run_pr(head=head)

    assert not result.blocks
    assert result.report.outcome == "SYNC"


def test_pr_accepts_one_stale_canonical_workflow(pr_repo: PressRepo) -> None:
    head = prepare_workflow_sync(pr_repo, (".github/workflows/check.yml",))

    result = pr_repo.run_pr(head=head)

    assert not result.blocks
    assert result.report.outcome == "SYNC"


def test_workflow_sync_rejects_an_extra_file(pr_repo: PressRepo) -> None:
    head = prepare_workflow_sync(pr_repo)
    pr_repo.write("unexpected.txt", "not part of a sync\n")
    pr_repo.commit("sneak in another file")

    result = pr_repo.run_pr(head=head)

    assert "B-WORKFLOW-SYNC" in result.blocks


def test_workflow_sync_rejects_a_noncanonical_blob(pr_repo: PressRepo) -> None:
    head = prepare_workflow_sync(pr_repo)
    pr_repo.write(".github/workflows/check.yml", "name: changed in the PR\n")
    pr_repo.commit("change canonical workflow")
    pr_repo.write(".github/workflows/check.yml", "name: canonical check\n")

    result = pr_repo.run_pr(head=head)

    assert "B-WORKFLOW-SYNC" in result.blocks


def retract_on_a_curation_branch(pr_repo: PressRepo) -> None:
    pr_repo.checkout("library")
    pr_repo.write("library/semiconductors/tsmc.html", article())
    pr_repo.commit("published")
    pr_repo.checkout("owner/curation", new=True)
    pr_repo.git("rm", "-q", "library/semiconductors/tsmc.html")
    pr_repo.git("commit", "-qm", "retract")


def test_deletion_only_pr_without_the_owner_flag(pr_repo: PressRepo) -> None:
    retract_on_a_curation_branch(pr_repo)

    result = pr_repo.run_pr(head="owner/curation", deletions_by_owner=False)

    assert "B-DIFF-SHAPE" in result.blocks


def test_owner_curation_deletion_only_pr(pr_repo: PressRepo) -> None:
    retract_on_a_curation_branch(pr_repo)

    result = pr_repo.run_pr(head="owner/curation", deletions_by_owner=True)

    assert not result.blocks


def test_owner_curation_deleting_engine_files(pr_repo: PressRepo) -> None:
    retract_on_a_curation_branch(pr_repo)
    pr_repo.git("rm", "-q", "engine/duty.py")
    pr_repo.git("commit", "-qm", "stray deletion")

    result = pr_repo.run_pr(head="owner/curation", deletions_by_owner=True)

    assert "B-DIFF-SHAPE" in result.blocks
