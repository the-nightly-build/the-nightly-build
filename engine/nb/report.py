"""The findings a proof run collects, and how they reach the caller.

Findings come in two tiers. BLOCK findings are integrity failures and CI
refuses to publish on any of them. WARN findings are quality calibration:
agents treat them as revision notes and they block only when a series sets
strict true.
"""

import json


class Finding:
    def __init__(self, code, level, *, message, suggestion=None):
        self.code, self.level, self.message, self.suggestion = (
            code,
            level,
            message,
            suggestion,
        )

    def as_dict(self):
        d = {"code": self.code, "level": self.level, "message": self.message}
        if self.suggestion:
            d["suggestion"] = self.suggestion
        return d


class Report:
    def __init__(self, strict=False):
        self.findings = []
        self.strict = strict
        self.notes = []

    def block(self, code, msg, *, suggestion=None):
        finding = Finding(code, "BLOCK", message=msg, suggestion=suggestion)
        self.findings.append(finding)

    def warn(self, code, msg, *, suggestion=None):
        level = "BLOCK" if self.strict else "WARN"
        finding = Finding(code, level, message=msg, suggestion=suggestion)
        self.findings.append(finding)

    @property
    def blocks(self):
        return [f for f in self.findings if f.level == "BLOCK"]

    @property
    def warns(self):
        return [f for f in self.findings if f.level == "WARN"]


def emit(rep, as_json):
    blocks, warns = rep.blocks, rep.warns
    if as_json:
        print(
            json.dumps(
                {
                    "block_count": len(blocks),
                    "warn_count": len(warns),
                    "findings": [f.as_dict() for f in rep.findings],
                    "notes": rep.notes,
                },
                indent=2,
            )
        )
    else:
        for label, findings in (("BLOCK:", blocks), ("WARN: ", warns)):
            print(f"{label} {len(findings)}")
            for f in findings:
                print(f"  {f.code:<18} {f.message}")
                if f.suggestion:
                    print(f"  {'':<18} → {f.suggestion}")
        for n in rep.notes:
            print(f"note: {n}")
        print("verdict:", "PUBLISHABLE" if not blocks else "BLOCKED")
    return 0 if not blocks else 1
