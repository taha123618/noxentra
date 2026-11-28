"""Environment diagnostics for `noxentra doctor`."""

from __future__ import annotations

import os
import shutil
import stat
import sys
from dataclasses import dataclass

from noxentra.constants import USER_CONFIG_DIR
from noxentra.os_detect import CURRENT_OS

CORE_TOOLS = ("subfinder", "httpx", "nuclei", "nmap", "trivy", "semgrep", "gitleaks")


@dataclass
class DoctorCheck:
    """Single diagnostic check result."""

    name: str
    status: str  # ok | warn | fail
    detail: str


def run_diagnostics() -> list[DoctorCheck]:
    """Inspect Python, OS, config permissions, and core pipeline binaries."""
    checks: list[DoctorCheck] = []

    py_ver = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    py_ok = sys.version_info >= (3, 10)
    checks.append(DoctorCheck("python", "ok" if py_ok else "fail", f"Python {py_ver}"))

    os_ok = CURRENT_OS.system in ("linux", "macos")
    checks.append(
        DoctorCheck(
            "platform",
            "ok" if os_ok else "fail",
            f"{CURRENT_OS.system} (pkg_manager={CURRENT_OS.pkg_manager or 'none'})",
        )
    )

    git_path = shutil.which("git")
    checks.append(DoctorCheck("git", "ok" if git_path else "warn", git_path or "not found in PATH"))

    tmux_path = shutil.which("tmux")
    checks.append(
        DoctorCheck(
            "tmux",
            "ok" if tmux_path else "warn",
            tmux_path or "optional — background sessions disabled",
        )
    )

    if USER_CONFIG_DIR.exists():
        checks.append(DoctorCheck("config_dir", "ok", str(USER_CONFIG_DIR)))
    else:
        checks.append(DoctorCheck("config_dir", "warn", f"{USER_CONFIG_DIR} (will be created on first run)"))

    env_file = USER_CONFIG_DIR / ".env"
    if env_file.exists():
        mode = stat.S_IMODE(os.stat(env_file).st_mode)
        if mode & 0o077:
            checks.append(
                DoctorCheck("env_permissions", "warn", f"{env_file} mode {oct(mode)} (expected 0o600)")
            )
        else:
            checks.append(DoctorCheck("env_permissions", "ok", f"{env_file} mode 0o600"))
    else:
        checks.append(DoctorCheck("env_permissions", "ok", "no .env file present"))

    installed = [t for t in CORE_TOOLS if shutil.which(t)]
    missing = [t for t in CORE_TOOLS if not shutil.which(t)]
    status = "ok" if not missing else "warn"
    detail = f"{len(installed)}/{len(CORE_TOOLS)} installed"
    if missing:
        detail += f" (missing: {', '.join(missing)})"
    checks.append(DoctorCheck("pipeline_tools", status, detail))

    return checks
