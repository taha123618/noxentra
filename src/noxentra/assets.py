"""Attack Surface Intelligence & Asset Graph built from engagement targets and findings."""

from __future__ import annotations

import ipaddress
import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

from noxentra.findings import Finding
from noxentra.storage import write_json


@dataclass
class Asset:
    """Normalized discovered asset node."""

    kind: str  # domain | subdomain | ip | port | service | url | api | cert | repo | cloud
    value: str
    sources: list[str] = field(default_factory=list)
    first_seen: str = ""
    last_seen: str = ""
    metadata: dict = field(default_factory=dict)


@dataclass
class AssetEdge:
    """Directed relationship between two assets (`kind:value`)."""

    src: str
    dst: str
    relation: str  # has_subdomain | resolves_to | exposes | serves | hosts_api | has_cert


def _is_ip(host: str) -> bool:
    try:
        ipaddress.ip_address(host)
        return True
    except ValueError:
        return False


def _root_domain(host: str) -> str:
    parts = [p for p in host.lower().strip(".").split(".") if p]
    if len(parts) <= 2:
        return ".".join(parts)
    return ".".join(parts[-2:])


def _asset_key(kind: str, value: str) -> tuple[str, str]:
    return (kind, value)


def _node_id(kind: str, value: str) -> str:
    return f"{kind}:{value}"


def build_assets_from_findings(
    targets: list[str],
    findings: list[Finding],
    *,
    timestamp: str | None = None,
) -> tuple[list[Asset], list[AssetEdge]]:
    """Build a deduplicated asset inventory and relationship graph from targets + findings."""
    ts = timestamp or datetime.now(timezone.utc).isoformat()
    nodes: dict[tuple[str, str], Asset] = {}
    edges: dict[tuple[str, str, str], AssetEdge] = {}

    def _add_asset(kind: str, value: str, source: str, seen_at: str, meta: dict | None = None) -> Asset:
        key = _asset_key(kind, value)
        existing = nodes.get(key)
        if existing is None:
            existing = Asset(
                kind=kind,
                value=value,
                sources=[source] if source else [],
                first_seen=seen_at,
                last_seen=seen_at,
                metadata=dict(meta or {}),
            )
            nodes[key] = existing
        else:
            if source and source not in existing.sources:
                existing.sources.append(source)
            if seen_at and (not existing.last_seen or seen_at > existing.last_seen):
                existing.last_seen = seen_at
            if meta:
                existing.metadata.update({k: v for k, v in meta.items() if v is not None})
        return existing

    def _add_edge(src_kind: str, src_val: str, dst_kind: str, dst_val: str, relation: str) -> None:
        s = _node_id(src_kind, src_val)
        d = _node_id(dst_kind, dst_val)
        edges[(s, d, relation)] = AssetEdge(src=s, dst=d, relation=relation)

    for raw_t in targets:
        t = raw_t.strip()
        if not t:
            continue
        if t.startswith(("http://", "https://")):
            parsed = urlparse(t)
            host = parsed.hostname or ""
            _add_asset("url", t, "target", ts)
            if host:
                kind = "ip" if _is_ip(host) else ("domain" if host == _root_domain(host) else "subdomain")
                _add_asset(kind, host, "target", ts)
                _add_edge(kind, host, "url", t, "serves")
        elif _is_ip(t):
            _add_asset("ip", t, "target", ts)
        elif "/" in t and Path(t).exists():
            _add_asset("repo", t, "target", ts)
        else:
            root = _root_domain(t)
            if root != t:
                _add_asset("domain", root, "target", ts)
                _add_asset("subdomain", t, "target", ts)
                _add_edge("domain", root, "subdomain", t, "has_subdomain")
            else:
                _add_asset("domain", t, "target", ts)

    for f in findings:
        seen_at = f.timestamp or ts
        src = f.source_tool
        if f.kind == "subdomain":
            host = f.target.strip()
            if not host:
                continue
            root = _root_domain(host)
            _add_asset("subdomain" if root != host else "domain", host, src, seen_at)
            if root != host:
                _add_asset("domain", root, src, seen_at)
                _add_edge("domain", root, "subdomain", host, "has_subdomain")
            for ip in f.details.get("a") or []:
                if isinstance(ip, str) and ip:
                    _add_asset("ip", ip, src, seen_at)
                    _add_edge("subdomain" if root != host else "domain", host, "ip", ip, "resolves_to")
        elif f.kind == "service":
            tgt = f.target.strip()
            if tgt.startswith(("http://", "https://")):
                parsed = urlparse(tgt)
                host = parsed.hostname or ""
                kind = "api" if "/api" in (parsed.path or "").lower() else "url"
                _add_asset(kind, tgt, src, seen_at, {"status_code": f.details.get("status_code")})
                if host:
                    hkind = "ip" if _is_ip(host) else ("domain" if host == _root_domain(host) else "subdomain")
                    _add_asset(hkind, host, src, seen_at)
                    _add_edge(hkind, host, kind, tgt, "serves")
            elif f.source_tool == "nmap" and tgt:
                hkind = "ip" if _is_ip(tgt) else "subdomain"
                _add_asset(hkind, tgt, src, seen_at)
                port = f.details.get("port")
                proto = f.details.get("proto") or "tcp"
                if port:
                    port_val = f"{tgt}:{port}/{proto}"
                    _add_asset("port", port_val, src, seen_at, {"service": f.details.get("service")})
                    _add_edge(hkind, tgt, "port", port_val, "exposes")
            elif f.source_tool == "tlsx" and tgt:
                hkind = "ip" if _is_ip(tgt) else "subdomain"
                _add_asset(hkind, tgt, src, seen_at)
                cn = f.details.get("subject_cn") or tgt
                _add_asset("cert", cn, src, seen_at, {"sans": f.details.get("subject_an")})
                _add_edge(hkind, tgt, "cert", cn, "has_cert")
        elif f.kind in ("secret", "misconfiguration", "iam-risk"):
            if f.kind == "iam-risk" or f.source_tool in ("cloudsplaining", "terrascan", "kube-hunter", "kube-linter"):
                _add_asset("cloud", f.target, src, seen_at)
            elif ":" in f.target:
                repo_path = f.target.split(":", 1)[0]
                _add_asset("repo", repo_path, src, seen_at)

    sorted_assets = sorted(nodes.values(), key=lambda a: (a.kind, a.value))
    sorted_edges = sorted(edges.values(), key=lambda e: (e.src, e.relation, e.dst))
    return sorted_assets, sorted_edges


def diff_assets(previous: list[Asset], current: list[Asset]) -> dict[str, list[Asset]]:
    """Compare two asset snapshots and return `added` and `removed` assets."""
    prev_map = {_asset_key(a.kind, a.value): a for a in previous}
    curr_map = {_asset_key(a.kind, a.value): a for a in current}
    added = [curr_map[k] for k in sorted(curr_map.keys() - prev_map.keys())]
    removed = [prev_map[k] for k in sorted(prev_map.keys() - curr_map.keys())]
    return {"added": added, "removed": removed}


def save_assets(path: Path, assets: list[Asset], edges: list[AssetEdge]) -> None:
    """Persist asset inventory and graph edges atomically."""
    write_json(
        path,
        {
            "assets": [asdict(a) for a in assets],
            "edges": [asdict(e) for e in edges],
        },
        indent=2,
    )


def load_assets(path: Path) -> tuple[list[Asset], list[AssetEdge]]:
    """Load persisted asset inventory and edges, returning empty lists if missing/invalid."""
    if not path.exists():
        return [], []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return [], []
    if not isinstance(data, dict):
        return [], []
    assets = [Asset(**a) for a in data.get("assets", []) if isinstance(a, dict)]
    edges = [AssetEdge(**e) for e in data.get("edges", []) if isinstance(e, dict)]
    return assets, edges


def render_graph_text(assets: list[Asset], edges: list[AssetEdge]) -> str:
    """Render a deterministic human-readable attack-surface graph summary."""
    lines = [f"Assets: {len(assets)} | Relationships: {len(edges)}"]
    for e in edges:
        lines.append(f"  {e.src} --[{e.relation}]--> {e.dst}")
    return "\n".join(lines)
