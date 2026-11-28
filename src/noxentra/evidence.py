"""Digital Evidence Management for engagement runs and findings traceability."""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

from noxentra.storage import write_json, write_text


@dataclass
class EvidenceRecord:
    """Immutable metadata describing a captured engagement artifact."""

    id: str
    tool: str
    execution_id: str
    artifact_type: str  # raw_output | http_response | log | pcap | screenshot | file
    path: str
    sha256: str
    size_bytes: int
    timestamp: str
    target: str = ""
    command: list[str] | None = None


def _manifest_path(workspace: Path) -> Path:
    return workspace / "evidence" / "manifest.json"


def load_manifest(workspace: Path) -> list[EvidenceRecord]:
    """Load all recorded evidence entries for an engagement workspace."""
    path = _manifest_path(workspace)
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []
    if not isinstance(data, list):
        return []
    return [EvidenceRecord(**item) for item in data if isinstance(item, dict)]


def record_evidence(
    workspace: Path,
    *,
    tool: str,
    execution_id: str,
    raw_output: str,
    command: list[str] | None = None,
    artifact_type: str = "raw_output",
    target: str = "",
    timestamp: str | None = None,
) -> EvidenceRecord:
    """Persist raw evidence atomically under `workspace/evidence/` and update `manifest.json`."""
    ts = timestamp or datetime.now(timezone.utc).isoformat()
    ev_id = f"ev-{uuid.uuid4().hex[:12]}"
    ev_dir = workspace / "evidence"
    ev_dir.mkdir(parents=True, exist_ok=True)

    safe_tool = "".join(c if c.isalnum() or c in "-_" else "_" for c in tool) or "tool"
    rel_path = f"evidence/{ev_id}-{safe_tool}.txt"
    full_path = workspace / rel_path
    write_text(full_path, raw_output)

    digest = hashlib.sha256(raw_output.encode("utf-8", errors="replace")).hexdigest()
    rec = EvidenceRecord(
        id=ev_id,
        tool=tool,
        execution_id=execution_id,
        artifact_type=artifact_type,
        path=rel_path,
        sha256=digest,
        size_bytes=len(raw_output.encode("utf-8", errors="replace")),
        timestamp=ts,
        target=target,
        command=list(command) if command else None,
    )
    manifest = load_manifest(workspace)
    manifest.append(rec)
    write_json(_manifest_path(workspace), [asdict(r) for r in manifest], indent=2)
    return rec


def verify_evidence(workspace: Path, record: EvidenceRecord) -> bool:
    """Verify an evidence file still exists and matches its recorded SHA-256 digest."""
    full_path = workspace / record.path
    if not full_path.exists():
        return False
    digest = hashlib.sha256(full_path.read_bytes()).hexdigest()
    return digest == record.sha256
