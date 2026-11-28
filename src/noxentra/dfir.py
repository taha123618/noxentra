"""DFIR & Threat Hunting Workspace (cases, artifact ingestion, timelines, YARA/Sigma)."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from noxentra.constants import USER_CONFIG_DIR
from noxentra.storage import write_json

CASES_ROOT = USER_CONFIG_DIR / "cases"


@dataclass
class TimelineEvent:
    """Single chronological event in a DFIR investigation."""

    timestamp: str
    source: str
    summary: str
    severity: str = "info"


@dataclass
class DfirArtifact:
    """Ingested forensic artifact with SHA-256 integrity hash."""

    name: str
    path: str
    sha256: str
    size_bytes: int
    ingested_at: str


@dataclass
class DfirCase:
    """Persistent DFIR & threat-hunting case."""

    name: str
    description: str = ""
    created_at: str = ""
    artifacts: list[DfirArtifact] = field(default_factory=list)
    timeline: list[TimelineEvent] = field(default_factory=list)

    @property
    def workspace(self) -> Path:
        return CASES_ROOT / self.name

    def save(self) -> None:
        self.workspace.mkdir(parents=True, exist_ok=True)
        write_json(self.workspace / "case.json", asdict(self), indent=2)


def create_case(name: str, description: str = "") -> DfirCase:
    """Create and persist a new DFIR case workspace."""
    case = DfirCase(
        name=name,
        description=description,
        created_at=datetime.now(timezone.utc).isoformat(),
    )
    case.save()
    return case


def load_case(name: str) -> DfirCase | None:
    """Load an existing DFIR case by name."""
    path = CASES_ROOT / name / "case.json"
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    return DfirCase(
        name=data["name"],
        description=data.get("description", ""),
        created_at=data.get("created_at", ""),
        artifacts=[DfirArtifact(**a) for a in data.get("artifacts", [])],
        timeline=[TimelineEvent(**e) for e in data.get("timeline", [])],
    )


def ingest_artifact(case: DfirCase, src_path: Path) -> DfirArtifact:
    """Hash and record a forensic artifact into the case."""
    raw = src_path.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    art = DfirArtifact(
        name=src_path.name,
        path=str(src_path),
        sha256=digest,
        size_bytes=len(raw),
        ingested_at=datetime.now(timezone.utc).isoformat(),
    )
    case.artifacts.append(art)
    case.timeline.append(
        TimelineEvent(
            timestamp=art.ingested_at,
            source="ingest",
            summary=f"Ingested {src_path.name} (sha256={digest[:12]})",
        )
    )
    case.save()
    return art
