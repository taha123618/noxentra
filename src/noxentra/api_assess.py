"""Dedicated API Security Assessment (OpenAPI/Swagger, Postman, JWT, misconfigurations)."""

from __future__ import annotations

import base64
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import yaml

from noxentra.findings import Finding


@dataclass
class ApiEndpoint:
    """Normalized REST or GraphQL endpoint from an API specification."""

    method: str
    path: str
    auth_schemes: list[str] = field(default_factory=list)
    parameters: list[str] = field(default_factory=list)
    summary: str = ""


def _load_spec(path: Path) -> dict:
    raw = path.read_text(encoding="utf-8")
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        data = yaml.safe_load(raw)
    if not isinstance(data, dict):
        raise TypeError(f"Invalid API specification in {path}")
    return data


def parse_openapi(spec: dict) -> list[ApiEndpoint]:
    """Extract normalized endpoints from OpenAPI 3.x or Swagger 2.0 specs."""
    endpoints: list[ApiEndpoint] = []
    global_sec = [
        k for item in (spec.get("security") or [])
        if isinstance(item, dict) for k in item
    ]
    paths = spec.get("paths") or {}
    if not isinstance(paths, dict):
        return endpoints

    http_methods = {"get", "post", "put", "patch", "delete", "options", "head"}
    for path_str, path_item in paths.items():
        if not isinstance(path_item, dict):
            continue
        for method, op in path_item.items():
            if method.lower() not in http_methods or not isinstance(op, dict):
                continue
            op_sec = op.get("security")
            if op_sec is None:
                auth = list(global_sec)
            else:
                auth = [k for item in op_sec if isinstance(item, dict) for k in item]
            params = [
                str(p.get("name"))
                for p in (op.get("parameters") or [])
                if isinstance(p, dict) and p.get("name")
            ]
            endpoints.append(
                ApiEndpoint(
                    method=method.upper(),
                    path=str(path_str),
                    auth_schemes=auth,
                    parameters=params,
                    summary=str(op.get("summary") or ""),
                )
            )
    return endpoints


def parse_postman(collection: dict) -> list[ApiEndpoint]:
    """Extract normalized endpoints from a Postman v2.1 collection."""
    endpoints: list[ApiEndpoint] = []

    def _walk(items: list) -> None:
        for item in items:
            if not isinstance(item, dict):
                continue
            if isinstance(item.get("item"), list):
                _walk(item["item"])
                continue
            req = item.get("request")
            if not isinstance(req, dict):
                continue
            method = str(req.get("method") or "GET").upper()
            url_obj = req.get("url")
            if isinstance(url_obj, dict):
                raw_path = "/" + "/".join(str(p) for p in (url_obj.get("path") or []))
                if raw_path == "/":
                    raw_path = str(url_obj.get("raw") or "/")
            else:
                raw_path = str(url_obj or "/")
            auth_obj = req.get("auth") if isinstance(req.get("auth"), dict) else {}
            auth = [str(auth_obj["type"])] if auth_obj.get("type") else []
            endpoints.append(
                ApiEndpoint(
                    method=method,
                    path=raw_path,
                    auth_schemes=auth,
                    summary=str(item.get("name") or ""),
                )
            )

    _walk(collection.get("item") or [])
    return endpoints


def audit_jwt(token: str, *, timestamp: str | None = None) -> list[Finding]:
    """Inspect a JWT header and payload for common configuration weaknesses."""
    ts = timestamp or datetime.now(timezone.utc).isoformat()
    parts = token.strip().split(".")
    if len(parts) < 2:
        return []

    def _b64json(seg: str) -> dict:
        padded = seg + "=" * (-len(seg) % 4)
        try:
            return json.loads(base64.urlsafe_b64decode(padded.encode("ascii")))
        except (ValueError, json.JSONDecodeError):
            return {}

    header = _b64json(parts[0])
    payload = _b64json(parts[1])
    findings: list[Finding] = []
    alg = str(header.get("alg") or "").lower()
    if alg == "none" or not alg:
        findings.append(
            Finding(
                kind="vulnerability",
                target="jwt",
                name="JWT uses insecure 'alg=none' (CWE-347)",
                severity="critical",
                source_tool="api_assess",
                details={"alg": header.get("alg"), "cwe": "CWE-347"},
                raw=token[:48],
                timestamp=ts,
            )
        )
    if "exp" not in payload:
        findings.append(
            Finding(
                kind="misconfiguration",
                target="jwt",
                name="JWT missing expiration ('exp') claim (CWE-287)",
                severity="medium",
                source_tool="api_assess",
                details={"claims": sorted(payload.keys()), "cwe": "CWE-287"},
                raw=token[:48],
                timestamp=ts,
            )
        )
    return findings


def audit_api_spec(path: Path, *, timestamp: str | None = None) -> tuple[list[ApiEndpoint], list[Finding]]:
    """Load an OpenAPI/Swagger or Postman spec and emit inventory + security findings."""
    ts = timestamp or datetime.now(timezone.utc).isoformat()
    spec = _load_spec(path)
    findings: list[Finding] = []

    if "info" in spec and "item" in spec:
        endpoints = parse_postman(spec)
    else:
        endpoints = parse_openapi(spec)
        for srv in spec.get("servers") or []:
            if isinstance(srv, dict):
                url = str(srv.get("url") or "")
                if url.startswith("http://"):
                    findings.append(
                        Finding(
                            kind="misconfiguration",
                            target=url,
                            name="API server uses unencrypted HTTP transport",
                            severity="medium",
                            source_tool="api_assess",
                            details={"server": url},
                            raw=url,
                            timestamp=ts,
                        )
                    )

    for ep in endpoints:
        if not ep.auth_schemes and ep.method in ("POST", "PUT", "PATCH", "DELETE"):
            findings.append(
                Finding(
                    kind="misconfiguration",
                    target=f"{ep.method} {ep.path}",
                    name=f"Unauthenticated state-changing API endpoint {ep.method} {ep.path} (CWE-287)",
                    severity="high",
                    source_tool="api_assess",
                    details={"method": ep.method, "path": ep.path, "cwe": "CWE-287"},
                    raw=f"{ep.method} {ep.path}",
                    timestamp=ts,
                )
            )
    return endpoints, findings
