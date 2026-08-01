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
        unique_codes = {finding.code for finding in self._findings}
        return sorted(unique_codes)

    def __repr__(self) -> str:
        if not self._findings:
            return "<none>"
        return "\n" + "\n".join(f"  {f.code:<18} {f.message}" for f in self._findings)


class Findings:
    def __init__(self, report: Report) -> None:
        self.report = report
        self.blocks = Tier(report.blocks)
        self.warns = Tier(report.warns)

    @property
    def codes(self) -> list[str]:
        unique_codes = {finding.code for finding in self.report.findings}
        return sorted(unique_codes)

    @property
    def notes(self) -> list[str]:
        return self.report.notes

    def __repr__(self) -> str:
        return f"Findings(blocks={self.blocks!r}\nwarns={self.warns!r}\n)"
