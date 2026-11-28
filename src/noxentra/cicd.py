"""DevSecOps & CI/CD gating helpers (severity thresholds, baseline diff, exit codes)."""

from __future__ import annotations

from dataclasses import dataclass

from noxentra.findings import Finding, diff_findings


@dataclass
class GateResult:
    """Machine-readable CI/CD policy gate evaluation."""

    passed: bool
    exit_code: int
    counts: dict[str, int]
    reason: str


def evaluate_gate(
    findings: list[Finding],
    *,
    max_critical: int = 0,
    max_high: int | None = None,
    baseline: list[Finding] | None = None,
) -> GateResult:
    """Evaluate findings (or net-new findings vs `baseline`) against severity thresholds."""
    target_set = findings
    if baseline is not None:
        existing_keys = {(f.kind, f.target, f.name, f.source_tool) for f in baseline}
        _, _ = diff_findings(baseline, findings)
        target_set = [
            f for f in findings
            if (f.kind, f.target, f.name, f.source_tool) not in existing_keys
        ]

    counts = {"critical": 0, "high": 0, "medium": 0, "low": 0, "info": 0, "unknown": 0}
    for f in target_set:
        sev = f.severity.lower()
        counts[sev if sev in counts else "unknown"] += 1

    breaches: list[str] = []
    if counts["critical"] > max_critical:
        breaches.append(f"critical={counts['critical']} > max_critical={max_critical}")
    if max_high is not None and counts["high"] > max_high:
        breaches.append(f"high={counts['high']} > max_high={max_high}")

    if breaches:
        return GateResult(
            passed=False,
            exit_code=1,
            counts=counts,
            reason="; ".join(breaches),
        )
    return GateResult(
        passed=True,
        exit_code=0,
        counts=counts,
        reason="policy gate passed",
    )
