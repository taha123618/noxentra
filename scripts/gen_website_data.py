"""Regenerate website catalog and search data from live Noxentra modules.

Run: uv run python scripts/gen_website_data.py
"""
import json
import re
from pathlib import Path

import noxentra.orchestrator as orch
import noxentra.toolbox as tb

ROOT = Path(__file__).resolve().parent.parent
WEBSITE_JS = ROOT / "website" / "js"
SEARCH_INDEX = WEBSITE_JS / "search-index.js"
CATALOG_JS = WEBSITE_JS / "catalog.js"


def build_data() -> tuple[list[dict], list[dict], list[dict]]:
    """Collect active catalog categories, flat search tools, and pipelines."""
    categories: list[dict] = []
    search_tools: list[dict] = []
    for cat in tb.all_tools[:-1]:
        tools = []
        for t in cat.TOOLS:
            if getattr(t, "ARCHIVED", False):
                continue
            tools.append({
                "title": t.TITLE,
                "desc": (getattr(t, "DESCRIPTION", "") or "").strip(),
                "tags": list(getattr(t, "TAGS", []) or []),
                "url": getattr(t, "PROJECT_URL", "") or "",
                "kind": getattr(t, "KIND", "install"),
            })
            search_tools.append({
                "t": t.TITLE,
                "c": cat.TITLE,
                "g": list(getattr(t, "TAGS", []) or []),
            })
        categories.append({"category": cat.TITLE, "count": len(tools), "tools": tools})
    pipelines = [{"n": p["name"], "d": p["description"]} for p in orch.list_pipelines()]
    return categories, search_tools, pipelines


def main() -> None:
    categories, search_tools, pipelines = build_data()
    SEARCH_INDEX.write_text(
        "window.NOXENTRA_SEARCH = "
        + json.dumps({"tools": search_tools, "pipelines": pipelines}, ensure_ascii=False)
        + ";\n"
    )
    catalog_src = CATALOG_JS.read_text()
    new_line = "const CATALOG = " + json.dumps(categories, ensure_ascii=False) + ";"
    updated = re.sub(r"^const CATALOG = .*?;$", lambda _: new_line, catalog_src, count=1, flags=re.MULTILINE)
    if updated == catalog_src and new_line not in catalog_src:
        raise RuntimeError(f"Could not find `const CATALOG = ...;` in {CATALOG_JS}")
    CATALOG_JS.write_text(updated)
    print(f"wrote {SEARCH_INDEX.name} and {CATALOG_JS.name} — {len(search_tools)} tools, {len(pipelines)} pipelines")


if __name__ == "__main__":
    main()
