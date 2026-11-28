"""Centralized Security Policy Engine & Configurable Assessment Profiles."""

from __future__ import annotations

from dataclasses import dataclass
from fnmatch import fnmatch
from urllib.parse import urlparse

RISK_ORDER = {"low": 0, "moderate": 1, "high": 2, "restricted": 3}

RESTRICTED_TOOLS = frozenset({
    "goldeneye", "slowloris", "saphyra", "hping3", "blackphish", "zphisher",
    "shellphish", "setoolkit", "msfconsole", "msfvenom", "metasploit",
})
HIGH_RISK_TOOLS = frozenset({
    "hydra", "medusa", "crowbar", "patator", "sqlmap", "commix", "nuclei",
    "ffuf", "gobuster", "feroxbuster", "dirb", "nikto", "wpscan",
})
MODERATE_RISK_TOOLS = frozenset({
    "nmap", "masscan", "naabu", "httpx", "katana", "tlsx", "whatweb",
    "kube-hunter", "prowler", "scoutsuite",
})


@dataclass(frozen=True)
class AssessmentProfile:
    """Policy configuration governing execution scope, concurrency, and risk limits."""

    name: str
    description: str
    max_risk: str  # low | moderate | high | restricted
    allow_active: bool
    max_concurrency: int
    step_timeout: int
    rate_limit_rps: int
    require_approval: bool


PROFILES: dict[str, AssessmentProfile] = {
    "passive_recon": AssessmentProfile(
        name="passive_recon",
        description="Passive OSINT, DNS, and offline static checks only (no active probing).",
        max_risk="low",
        allow_active=False,
        max_concurrency=2,
        step_timeout=600,
        rate_limit_rps=5,
        require_approval=False,
    ),
    "safe_active": AssessmentProfile(
        name="safe_active",
        description="Non-intrusive probing and bounded enumeration on authorized targets.",
        max_risk="moderate",
        allow_active=True,
        max_concurrency=4,
        step_timeout=1200,
        rate_limit_rps=25,
        require_approval=False,
    ),
    "full_authorized": AssessmentProfile(
        name="full_authorized",
        description="Full authorized assessment including vulnerability scanning and fuzzing.",
        max_risk="high",
        allow_active=True,
        max_concurrency=6,
        step_timeout=1800,
        rate_limit_rps=100,
        require_approval=True,
    ),
    "lab_ctf": AssessmentProfile(
        name="lab_ctf",
        description="Isolated lab or CTF environment allowing restricted tooling.",
        max_risk="restricted",
        allow_active=True,
        max_concurrency=8,
        step_timeout=1800,
        rate_limit_rps=0,
        require_approval=True,
    ),
    "defensive_forensic": AssessmentProfile(
        name="defensive_forensic",
        description="Offline DFIR, SAST, SCA, secret scanning, and threat hunting.",
        max_risk="low",
        allow_active=False,
        max_concurrency=4,
        step_timeout=1800,
        rate_limit_rps=0,
        require_approval=False,
    ),
}


@dataclass
class PolicyDecision:
    """Result of evaluating a tool execution against a policy profile and scope."""

    allowed: bool
    reason: str
    tool_risk: str
    effective_targets: list[str]
    max_concurrency: int
    step_timeout: int


def get_profile(name: str) -> AssessmentProfile:
    """Return a named assessment profile or raise ValueError."""
    if name not in PROFILES:
        valid = ", ".join(sorted(PROFILES))
        raise ValueError(f"Unknown assessment profile {name!r}; expected one of: {valid}")
    return PROFILES[name]


def classify_tool_risk(tool_name: str, tags: list[str] | tuple[str, ...] = ()) -> str:
    """Classify a tool into `low`, `moderate`, `high`, or `restricted` risk."""
    low = tool_name.strip().lower()
    tag_set = {t.lower() for t in tags}
    if low in RESTRICTED_TOOLS or tag_set & {"dos", "phishing", "exploit", "post-exploitation", "c2"}:
        return "restricted"
    if low in HIGH_RISK_TOOLS or tag_set & {"bruteforce", "password-attack", "fuzzing", "sqli"}:
        return "high"
    if low in MODERATE_RISK_TOOLS or tag_set & {"port-scan", "crawler", "active-recon"}:
        return "moderate"
    return "low"


def _host_of(target: str) -> str:
    if "://" in target:
        return (urlparse(target).hostname or target).lower()
    return target.split("/")[0].split(":")[0].lower()


def evaluate_execution(
    profile: AssessmentProfile | str,
    tool_name: str,
    targets: list[str],
    *,
    scope_out: list[str] | tuple[str, ...] = (),
    tags: list[str] | tuple[str, ...] = (),
) -> PolicyDecision:
    """Enforce profile risk limits, active/passive rules, and scope_out exclusions."""
    prof = get_profile(profile) if isinstance(profile, str) else profile
    risk = classify_tool_risk(tool_name, tags)
    filtered = [
        t for t in targets
        if not any(fnmatch(_host_of(t), pat) for pat in scope_out)
    ]

    if RISK_ORDER[risk] > RISK_ORDER[prof.max_risk]:
        return PolicyDecision(
            allowed=False,
            reason=f"Tool '{tool_name}' risk '{risk}' exceeds profile '{prof.name}' max '{prof.max_risk}'",
            tool_risk=risk,
            effective_targets=filtered,
            max_concurrency=prof.max_concurrency,
            step_timeout=prof.step_timeout,
        )

    if not prof.allow_active and risk in ("moderate", "high", "restricted"):
        return PolicyDecision(
            allowed=False,
            reason=f"Profile '{prof.name}' disallows active tool '{tool_name}' (risk={risk})",
            tool_risk=risk,
            effective_targets=filtered,
            max_concurrency=prof.max_concurrency,
            step_timeout=prof.step_timeout,
        )

    return PolicyDecision(
        allowed=True,
        reason="allowed",
        tool_risk=risk,
        effective_targets=filtered,
        max_concurrency=prof.max_concurrency,
        step_timeout=prof.step_timeout,
    )
