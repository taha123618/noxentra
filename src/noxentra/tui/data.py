"""Read-only view of the engine's categories/tools for the TUI. No Textual here."""
from dataclasses import dataclass


@dataclass
class CatRow:
    index: int        # position in cli.all_tools
    title: str
    icon: str
    label: str
    count: int        # active, OS-compatible tools


@dataclass
class ToolRow:
    index: int        # position within the category's active tool list
    title: str
    description: str
    url: str
    installed: bool
    obj: object       # live Noxentra instance (for install/run/uninstall)


def _engine():
    import noxentra.cli as cli
    return cli.all_tools, cli.tool_definitions


def categories() -> list[CatRow]:
    all_tools, defs = _engine()
    rows = []
    for i, (coll, (title, icon, label)) in enumerate(zip(all_tools, defs)):
        active = coll._active_tools() if hasattr(coll, "_active_tools") else list(coll.TOOLS)
        rows.append(CatRow(index=i, title=title, icon=icon, label=label, count=len(active)))
    return rows


def _active_tools(cat_index: int) -> list:
    all_tools, _ = _engine()
    coll = all_tools[cat_index]
    return coll._active_tools() if hasattr(coll, "_active_tools") else list(coll.TOOLS)


def tools_in(cat_index: int) -> list[ToolRow]:
    rows = []
    for j, t in enumerate(_active_tools(cat_index)):
        try:
            installed = bool(t.is_installed())
        except Exception:
            installed = False
        rows.append(ToolRow(
            index=j,
            title=getattr(t, "TITLE", "?"),
            description=getattr(t, "DESCRIPTION", "") or "",
            url=getattr(t, "PROJECT_URL", "") or "",
            installed=installed,
            obj=t,
        ))
    return rows


def tool_at(cat_index: int, tool_index: int) -> ToolRow:
    return tools_in(cat_index)[tool_index]


@dataclass
class ToolHit:
    cat_index: int
    tool_index: int
    title: str
    cat_label: str


def search_tools(needle: str) -> list[ToolHit]:
    """All tools (across every category) whose title OR category name matches.
    Title-only read — no is_installed() probing, so main-screen search stays fast."""
    n = needle.lower().strip()
    if not n:
        return []
    hits: list[ToolHit] = []
    for cat in categories():
        cat_hit = n in cat.label.lower()
        for j, t in enumerate(_active_tools(cat.index)):
            title = getattr(t, "TITLE", "?")
            if cat_hit or n in title.lower():
                hits.append(ToolHit(cat.index, j, title, cat.label))
    return hits


@dataclass
class EngagementRow:
    name: str
    targets_count: int
    findings_count: int
    created: str
    obj: object


def recommend_tools(intent: str) -> tuple[list[str], list[ToolHit]]:
    """Resolve free-text intent -> (matched_tags, matching ToolHits)."""
    import difflib
    import noxentra.ai_recommend as ai_recommend
    import noxentra.cli as cli

    q = intent.strip()
    if not q:
        return [], []

    cats = categories()
    all_tags: set[str] = set()
    tool_rows: list[tuple[ToolHit, set[str]]] = []
    for cat in cats:
        for j, t in enumerate(_active_tools(cat.index)):
            tags = {str(tg).lower() for tg in getattr(t, "TAGS", ()) or ()}
            all_tags.update(tags)
            tool_rows.append((ToolHit(cat.index, j, getattr(t, "TITLE", "?"), cat.label), tags))

    close = difflib.get_close_matches(q.lower(), cli._RECOMMENDATIONS, n=1, cutoff=0.6)
    if close:
        tag_names = list(cli._RECOMMENDATIONS[close[0]])
    else:
        tag_names = ai_recommend.resolve(q, sorted(all_tags))

    wanted = {tg.lower() for tg in tag_names}
    hits = [hit for hit, tags in tool_rows if tags & wanted]
    return tag_names, hits


def engagements() -> list[EngagementRow]:
    """List persisted engagements under ENGAGEMENTS_ROOT, newest first."""
    from noxentra import engagement, findings

    root = engagement.ENGAGEMENTS_ROOT
    if not root.exists():
        return []
    rows: list[EngagementRow] = []
    for entry in root.iterdir():
        if not entry.is_dir():
            continue
        try:
            e = engagement.load(entry.name)
        except (ValueError, OSError):
            continue
        if e is None:
            continue
        found = findings.load_findings(e.findings_file)
        rows.append(EngagementRow(
            name=e.name,
            targets_count=len(e.targets),
            findings_count=len(found),
            created=e.created,
            obj=e,
        ))
    rows.sort(key=lambda r: r.created, reverse=True)
    return rows
