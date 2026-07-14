"""What the proof said, addressed by tier.

The old suite asserted that a finding's code appeared. It never asserted the
tier, so flipping a check from rep.block to rep.warn left every test green.
Here a tier is the thing you assert against:

    assert "B-SOURCE-KIND" in result.blocks   # fails if it demotes to a warn
    assert "W-CITE-DENSITY" in result.warns   # fails if it hardens to a block
    assert not result.blocks                  # the article is publishable

`in` asks about codes; len() counts findings, because one code can be raised
once per offending source. Absence is the one question a tier cannot answer on
its own — a demoted finding is still absent from .blocks — so ask result.codes,
which spans every tier.
"""

from check import Finding, Report


class Tier:
    """The findings the proof raised at one level."""

    def __init__(self, findings: list[Finding]) -> None:
        self._findings = tuple(findings)

    def __contains__(self, code: str) -> bool:
        return any(f.code == code for f in self._findings)

    def __iter__(self):
        return iter(self._findings)

    def __len__(self) -> int:
        return len(self._findings)

    @property
    def codes(self) -> list[str]:
        return sorted({f.code for f in self._findings})

    def saying(self, fragment: str) -> bool:
        """Whether a finding at this tier carries `fragment` in its message.

        Several rules share a code (B-SANDBOX covers scripts, tags, handlers and
        external refs), so a code alone cannot tell which one fired. Where the
        rule matters on its own, name it.
        """
        return any(fragment in f.message for f in self._findings)

    def __repr__(self) -> str:
        if not self._findings:
            return "<none>"
        return "\n" + "\n".join(f"  {f.code:<18} {f.message}" for f in self._findings)


class Findings:
    """One proof run's verdict."""

    def __init__(self, report: Report) -> None:
        self.report = report
        self.blocks = Tier(report.blocks)
        self.warns = Tier(report.warns)

    @property
    def codes(self) -> list[str]:
        """Every code raised, at any tier. For asserting a finding is absent."""
        return sorted({f.code for f in self.report.findings})

    @property
    def notes(self) -> list[str]:
        return self.report.notes

    def __repr__(self) -> str:
        return f"Findings(blocks={self.blocks!r}\nwarns={self.warns!r}\n)"


def findings_of(report: Report) -> Findings:
    """Wrap a Report the test filled by calling into check.py directly."""
    return Findings(report)
