#!/usr/bin/env python3
import argparse
import datetime
import difflib
import os
import platform
import random
import socket
import sys
import webbrowser
from itertools import zip_longest
from pathlib import Path

from rich import box
from rich.panel import Panel
from rich.prompt import Confirm
from rich.rule import Rule
from rich.table import Table
from rich.text import Text

from noxentra import (
    ai_recommend,
    ai_report,
    ai_summary,
    engagement,
    orchestrator,
    report,
    update_check,
)
from noxentra.config import get_tools_dir
from noxentra.constants import REPO_WEB_URL, VERSION_DISPLAY
from noxentra.core import ask, clear_screen, console
from noxentra.toolbox import (
    RECOMMENDATIONS as _RECOMMENDATIONS,
)
from noxentra.toolbox import (
    AllTools,
    _reg,
    all_tools,
    tool_definitions,
)
from noxentra.toolbox import (
    collect_all_tools as _collect_all_tools,
)
from noxentra.toolbox import (
    get_all_tags as _get_all_tags,
)

__all__ = [
    "_RECOMMENDATIONS",
    "AllTools",
    "_collect_all_tools",
    "_get_all_tags",
    "_reg",
    "all_tools",
    "tool_definitions",
]

# ── Help overlay ───────────────────────────────────────────────────────────────

def show_help():
    console.print(Panel(
        Text.assemble(
            ("  Main menu\n", "bold white"),
            ("  ─────────────────────────────────────\n", "dim"),
            ("  type    ", "bold cyan"), ("just say what you want to do (e.g. crack a wifi handshake)\n", "white"),
            ("  1–N    ", "bold cyan"), ("open a category (last = Update / Uninstall)\n", "white"),
            ("  / or s ", "bold cyan"), ("search tools by name or keyword\n", "white"),
            ("  t      ", "bold cyan"), ("filter tools by tag (osint, web, c2, ...)\n", "white"),
            ("  r / a  ", "bold cyan"), ("recommend tools — pick a task or type it (e.g. r crack a hash)\n", "white"),
            ("  /goal  ", "bold cyan"), ("AI-plan & run an objective, one step at a time (e.g. /goal find subdomains of x.com)\n", "white"),
            ("  /find  ", "bold cyan"), ("find tools for a need — your toolbox + GitHub, suggest-only (e.g. /find hidden directories on a website)\n", "white"),
            ("  /engage ", "bold cyan"), ("create/open an engagement & run recon/web/cloud pipelines live\n", "white"),
            ("  /report ", "bold cyan"), ("export engagement findings as Markdown, HTML, or SARIF\n", "white"),
            ("  ?      ", "bold cyan"), ("show this help\n", "white"),
            ("  clear  ", "bold cyan"), ("clear the screen (also /clear)\n", "white"),
            ("  /config ", "bold cyan"), ("view/edit settings; /config test checks the AI connection\n", "white"),
            ("  /update ", "bold cyan"), ("update system packages or noxentra\n", "white"),
            ("  /uninstall ", "bold cyan"), ("remove noxentra + its installed tools\n", "white"),
            ("  q      ", "bold cyan"), ("quit — q, quit, exit, /quit, Ctrl-C, Ctrl-D\n\n", "white"),
            ("  Inside a category\n", "bold white"),
            ("  ─────────────────────────────────────\n", "dim"),
            ("  1–N    ", "bold cyan"), ("select a tool\n", "white"),
            ("  99     ", "bold cyan"), ("back to main menu\n", "white"),
            ("  98     ", "bold cyan"), ("archived tools (in a tool's menu: open project page)\n\n", "white"),
            ("  Inside a tool\n", "bold white"),
            ("  ─────────────────────────────────────\n", "dim"),
            ("  1      ", "bold cyan"), ("install tool\n", "white"),
            ("  2      ", "bold cyan"), ("run tool\n", "white"),
            ("  99     ", "bold cyan"), ("back to category\n", "white"),
        ),
        title="[bold magenta] ? Quick Help [/bold magenta]",
        border_style="magenta",
        box=box.ROUNDED,
        padding=(0, 2),
    ))
    ask("[dim]Press Enter to return[/dim]", default="")


# ── Header: ASCII art + live system info ──────────────────────────────────────

# Full "NOX ENTRA" block-letter art — 12 lines, split layout with stats
_BANNER_ART = [
    "     ███╗   ██╗ ██████╗ ██╗  ██╗",
    "     ████╗  ██║██╔═══██╗╚██╗██╔╝",
    "     ██╔██╗ ██║██║   ██║ ╚███╔╝ ",
    "     ██║╚██╗██║██║   ██║ ██╔██╗ ",
    "     ██║ ╚████║╚██████╔╝██╔╝ ██╗",
    "     ╚═╝  ╚═══╝ ╚═════╝ ╚═╝  ╚═╝",
    " ███████╗███╗   ██╗████████╗██████╗  █████╗ ",
    " ██╔════╝████╗  ██║╚══██╔══╝██╔══██╗██╔══██╗",
    " █████╗  ██╔██╗ ██║   ██║   ██████╔╝███████║",
    " ██╔══╝  ██║╚██╗██║   ██║   ██╔══██╗██╔══██║",
    " ███████╗██║ ╚████║   ██║   ██║  ██║██║  ██║",
    " ╚══════╝╚═╝  ╚═══╝   ╚═╝   ╚═╝  ╚═╝╚═╝  ╚═╝",
]

_QUOTES = [
    '"The quieter you become, the more you can hear."',
    '"Offense informs defense."',
    '"There is no patch for human stupidity."',
    '"In God we trust. All others we monitor."',
    '"Hackers are the immune system of the internet."',
    '"Every system is hackable — know yours before others do."',
    '"Enumerate before you exploit."',
    '"A scope defines your playground."',
    '"The more you sweat in training, the less you bleed in battle."',
    '"Security is a process, not a product."',
]


def _sys_info() -> dict:
    """Collect live system info for the header panel."""
    info: dict = {}

    # OS pretty name
    try:
        info["os"] = platform.freedesktop_os_release().get("PRETTY_NAME", "")
    except (OSError, AttributeError):
        info["os"] = ""
    if not info["os"]:
        info["os"] = f"{platform.system()} {platform.release()}"

    info["kernel"] = platform.release()

    # Current user
    try:
        info["user"] = os.getlogin()
    except OSError:
        info["user"] = os.environ.get("USER", os.environ.get("LOGNAME", "root"))

    info["host"] = socket.gethostname()

    # Local IP — connect to a routable address without sending data
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0)
        s.connect(("10.254.254.254", 1))
        info["ip"] = s.getsockname()[0]
        s.close()
    except OSError:
        info["ip"] = "127.0.0.1"

    info["time"] = datetime.datetime.now().strftime("%Y-%m-%d  %H:%M")
    return info


def _build_header() -> Panel:
    info = _sys_info()

    # Count real tools (active vs archived) so the header never overclaims.
    _all = _collect_all_tools()
    _active = sum(1 for t, _ in _all if not getattr(t, "ARCHIVED", False))
    _archived = len(_all) - _active

    # 12 stat lines paired with the 12 art lines
    stat_lines = [
        ("  os      ›  ", info["os"][:34]),
        ("  kernel  ›  ", info["kernel"][:34]),
        ("  user    ›  ", f"{info['user']} @ {info['host'][:20]}"),
        ("  ip      ›  ", info["ip"]),
        ("  tools   ›  ", f"{len(all_tools)} categories · {_active} active · {_archived} archived"),
        ("  session ›  ", info["time"]),
        ("", ""),
        ("  python  ›  ", f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"),
        ("  arch    ›  ", platform.machine()),
        ("  status  ›  ", "✔ READY"),
        ("", ""),
        ("", ""),
    ]

    grid = Table.grid(padding=0)
    grid.add_column("art", no_wrap=True)
    grid.add_column("sep", no_wrap=True)
    grid.add_column("lbl", no_wrap=True)
    grid.add_column("val", no_wrap=True)

    for art_line, (lbl_text, val_text) in zip(_BANNER_ART, stat_lines):
        grid.add_row(
            Text(art_line, style="bold bright_green"),
            Text("  │ ", style="dim green"),
            Text(lbl_text, style="dim green"),
            Text(val_text, style="bright_green"),
        )

    # Quote + warning below the split row
    quote = random.choice(_QUOTES)
    body = Table.grid(padding=(0, 0))
    body.add_column()
    body.add_row(grid)
    body.add_row(Text(""))
    body.add_row(Text(f"  {quote}", style="italic dim"))
    body.add_row(Text("  ⚠  For authorized security testing only",
                      style="bold dim red"))

    # Cached once-a-day check; prints nothing when up to date, offline, or opted out.
    if (newer := update_check.latest_if_newer()):
        body.add_row(Text(
            f"  ⬆  update available: v{newer}  (you have {VERSION_DISPLAY})  ·  "
            f"{REPO_WEB_URL}/releases",
            style="bold yellow"))

    return Panel(
        body,
        title=f"[bold bright_magenta][ Noxentra {VERSION_DISPLAY} ][/bold bright_magenta]",
        title_align="left",
        subtitle=f"[dim][ {info['time']} ][/dim]",
        subtitle_align="right",
        border_style="bright_magenta",
        box=box.HEAVY,
        padding=(0, 1),
    )


# ── Main menu renderer ─────────────────────────────────────────────────────────

def build_menu():
    clear_screen()
    console.print(_build_header())

    # ── 2-column category grid ──
    # Items 1-17 in two columns, item 18 (ToolManager) shown separately
    categories = tool_definitions[:-1]   # 17 items
    update_def = tool_definitions[-1]    # ToolManager

    mid = (len(categories) + 1) // 2    # 9  (left), 8 (right)
    left  = list(enumerate(categories[:mid],  start=1))
    right = list(enumerate(categories[mid:],  start=mid + 1))

    grid = Table.grid(padding=(0, 1), expand=True)
    grid.add_column("ln", justify="right", style="bold magenta", width=5)
    grid.add_column("li", width=3)
    grid.add_column("lt", style="magenta", ratio=1, no_wrap=True)
    grid.add_column("gap", width=3)
    grid.add_column("rn", justify="right", style="bold magenta", width=5)
    grid.add_column("ri", width=3)
    grid.add_column("rt", style="magenta", ratio=1, no_wrap=True)

    for (li, (_, lic, ll)), r in zip_longest(left, right, fillvalue=None):
        if r:
            ri, (_, ric, rl) = r
            grid.add_row(str(li), lic, ll, "", str(ri), ric, rl)
        else:
            grid.add_row(str(li), lic, ll, "", "", "", "")

    console.print(Panel(
        grid,
        title="[bold magenta] Select a Category [/bold magenta]",
        border_style="bright_magenta",
        box=box.ROUNDED,
        padding=(0, 1),
    ))

    # ── ToolManager row ──
    tm_num = len(categories) + 1
    console.print(
        f"  [bold magenta]  {tm_num}[/bold magenta]  {update_def[1]}  "
        f"[magenta]{update_def[2]}[/magenta]"
    )

    # ── Claude-style dual-line prompt area ──
    console.print(Rule(style="dim magenta"))
    console.print(
        "  [dim]type a number, or just say what you want to do[/dim]"
    )
    console.print(
        "  [dim cyan]/[/dim cyan][dim]search[/dim]  "
        "[dim cyan]t[/dim cyan] [dim]tags[/dim]  "
        "[dim cyan]r[/dim cyan] [dim]recommend[/dim]  "
        "[dim cyan]?[/dim cyan] [dim]help[/dim]  "
        "[dim cyan]q[/dim cyan] [dim]quit[/dim]"
    )


# ── Search ─────────────────────────────────────────────────────────────────────
# _collect_all_tools, _get_all_tags, and _RECOMMENDATIONS live in toolbox.py.


def _tool_table(matches, title):
    """Render the standard No/status/Tool/Category result table."""
    table = Table(title=title, box=box.SIMPLE_HEAD, show_lines=True)
    table.add_column("No.", justify="center", style="bold cyan", width=5)
    table.add_column("", width=2)
    table.add_column("Tool", style="bold yellow", min_width=20)
    table.add_column("Category", style="magenta", min_width=15)
    for i, (tool, cat) in enumerate(matches, start=1):
        status = "[green]✔[/green]" if tool.is_installed else "[dim]✘[/dim]"
        table.add_row(str(i), status, tool.TITLE, cat)
    table.add_row("b", "", "Back to main menu", "")
    console.print(table)


def _pick_tool(matches):
    """Prompt for a number and open that tool; ignore blank/back/invalid."""
    raw = ask("[bold cyan]>[/bold cyan]", default="").strip()
    if not raw or raw.lower() in ("b", "back"):
        return
    try:
        idx = int(raw)
    except ValueError:
        return
    if 1 <= idx <= len(matches):
        matches[idx - 1][0].show_options()


def _tools_for_tags(tag_names, tag_index):
    """Resolve tag names to a deduped [(tool, category)] list."""
    seen, matches = set(), []
    for tag in tag_names:
        for tool, cat in tag_index.get(tag, []):
            if id(tool) not in seen:
                seen.add(id(tool))
                matches.append((tool, cat))
    return matches


def filter_by_tag():
    """Show available tags, user picks one, show matching tools."""
    tag_index = _get_all_tags()
    sorted_tags = sorted(tag_index.keys())

    # Show tags in a compact grid
    console.print(Panel(
        "  ".join(f"[bold cyan]{t}[/bold cyan]([dim]{len(tag_index[t])}[/dim])" for t in sorted_tags),
        title="[bold magenta] Available Tags [/bold magenta]",
        border_style="magenta", box=box.ROUNDED, padding=(0, 2),
    ))

    tag = ask("[bold cyan]Enter tag[/bold cyan]", default="").strip().lower()
    if not tag or tag not in tag_index:
        if tag:
            console.print(f"[dim]Tag '{tag}' not found.[/dim]")
            ask("[dim]Press Enter to return[/dim]", default="")
        return

    matches = tag_index[tag]
    _tool_table(matches, f"Tools tagged '{tag}'")
    _pick_tool(matches)


def _show_recommended(matches, label):
    """Render recommended tools for a task and let the user open one."""
    if not matches:
        console.print("[dim]No matching tools found — try rephrasing.[/dim]")
        ask("[dim]Press Enter to return[/dim]", default="")
        return
    console.print(Panel(
        f"[bold]Recommended tools for: {label}[/bold]",
        border_style="green", box=box.ROUNDED,
    ))
    _tool_table(matches, None)
    _pick_tool(matches)


def _recommend_freetext(intent):
    """AI1: free-text intent -> tags -> tools; curated-phrase match takes priority."""
    tag_index = _get_all_tags()
    # A close paraphrase of a curated task reuses its hand-picked tags.
    close = difflib.get_close_matches(intent.lower(), _RECOMMENDATIONS, n=1, cutoff=0.6)
    if close:
        tag_names = _RECOMMENDATIONS[close[0]]
    else:
        tag_names = ai_recommend.resolve(intent, tag_index.keys())
    _show_recommended(_tools_for_tags(tag_names, tag_index), intent)


def recommend_tools(intent=None):
    """Recommend tools: pick a common task, or type what you want to do (AI1)."""
    if intent:
        _recommend_freetext(intent)
        return

    table = Table(title="What do you want to do?", box=box.SIMPLE_HEAD)
    table.add_column("No.", justify="center", style="bold cyan", width=5)
    table.add_column("Task", style="bold yellow")

    tasks = list(_RECOMMENDATIONS.keys())
    for i, task in enumerate(tasks, start=1):
        table.add_row(str(i), task.title())
    table.add_row("99", "Back to main menu")
    console.print(table)
    console.print("[dim]…or type what you want to do in your own words.[/dim]")

    raw = ask("[bold cyan]>[/bold cyan]", default="").strip()
    if not raw or raw == "99":
        return
    if raw.isdigit():
        idx = int(raw)
        if 1 <= idx <= len(tasks):
            task = tasks[idx - 1]
            tag_index = _get_all_tags()
            _show_recommended(
                _tools_for_tags(_RECOMMENDATIONS[task], tag_index), task.title())
        return
    _recommend_freetext(raw)


def search_tools(query: str | None = None):
    """Search tools — accepts inline query or prompts for one."""
    if query is None:
        query = ask("[bold cyan]/ Search[/bold cyan]", default="").strip().lower()
    else:
        query = query.lower()
    if not query:
        return

    all_tool_list = _collect_all_tools()

    # Match against title + description + tags
    matches = []
    for tool, category in all_tool_list:
        title = (tool.TITLE or "").lower()
        desc = (tool.DESCRIPTION or "").lower()
        tags = " ".join(getattr(tool, "TAGS", []) or []).lower()
        if query in title or query in desc or query in tags:
            matches.append((tool, category))

    if not matches:
        console.print(f"[dim]No tools found matching '{query}'[/dim]")
        ask("[dim]Press Enter to return[/dim]", default="")
        return

    # Display results
    table = Table(
        title=f"Search results for '{query}'",
        box=box.SIMPLE_HEAD, show_lines=True,
    )
    table.add_column("No.", justify="center", style="bold cyan", width=5)
    table.add_column("Tool", style="bold yellow", min_width=20)
    table.add_column("Category", style="magenta", min_width=15)
    table.add_column("Description", style="white", overflow="fold")

    for i, (tool, cat) in enumerate(matches, start=1):
        desc = (tool.DESCRIPTION or "—").splitlines()[0]
        table.add_row(str(i), tool.TITLE, cat, desc)

    table.add_row("b", "Back to main menu", "", "")
    console.print(table)

    _pick_tool(matches)


def config_command(arg: str = "") -> None:
    """/config surface: no arg → table; ``<key>`` → show; ``<key> <value>`` → set."""
    from noxentra import config
    from noxentra.constants import USER_CONFIG_FILE

    arg = (arg or "").strip()
    if arg == "test":                         # probe the configured AI transport
        from noxentra import ai_recommend
        ok, detail = ai_recommend.test_connection()
        label = "[success]✓ AI connection OK[/success]" if ok else "[error]✗ AI connection failed[/error]"
        console.print(f"{label}  [dim]{detail}[/dim]")
        return
    if arg == "github":                       # probe the configured GitHub token
        from noxentra import discover
        ok, detail = discover.check_token()
        label = ("[success]✓ GitHub token OK[/success]" if ok
                 else "[warning]○ GitHub[/warning]")
        console.print(f"{label}  [dim]{detail}[/dim]")
        if not ok:
            console.print(discover.GITHUB_TOKEN_STEPS)
        return
    if not arg:
        from noxentra import prompt
        if prompt._use_pt():                  # interactive TTY → full-screen modal editor
            from noxentra import config_ui
            config_ui.open_editor()
            return
        # non-TTY / --classic / no prompt_toolkit → read-only table
        table = Table(title="Settings", box=box.ROUNDED, border_style="magenta")
        table.add_column("key", style="cyan")
        table.add_column("value")
        table.add_column("", style="dim")
        for key, value, editable in config.describe():
            table.add_row(key, str(value), "" if editable else "read-only")
        console.print(table)
        console.print(f"[dim]{USER_CONFIG_FILE}  ·  "
                      "/config <key> <value> to change[/dim]")
        return

    parts = arg.split(maxsplit=1)
    key = parts[0]
    if len(parts) == 1:                       # show one key
        resolved = config._resolve_key(key)
        if resolved is None:
            console.print(f"[warning]Unknown or ambiguous key '{key}'.[/warning]")
            return
        value = config.load().get(resolved)
        hint = config.allowed_values(resolved)
        suffix = f"  [dim](allowed: {hint})[/dim]" if hint else ""
        console.print(f"[cyan]{resolved}[/cyan] = {value}{suffix}")
        return

    ok, msg = config.set_value(key, parts[1])
    console.print(f"[success]{msg}[/success]" if ok else f"[error]{msg}[/error]")


# ── Main interaction loop ──────────────────────────────────────────────────────

def interact_menu():
    while True:
        try:
            build_menu()
            raw = ask(
                "[bold magenta]╰─>[/bold magenta]", default=""
            ).strip()

            if not raw:
                continue

            raw_lower = raw.lower()

            if raw_lower in ("?", "help"):
                show_help()
                continue

            if raw.startswith("/"):
                # Inline search: /subdomain → search immediately
                query = raw[1:].strip()
                search_tools(query=query if query else None)
                continue

            if raw_lower in ("s", "search"):
                search_tools()
                continue

            if raw_lower in ("t", "tag", "tags", "filter"):
                filter_by_tag()
                continue

            parts = raw.split(maxsplit=1)
            if parts[0].lower() in ("r", "rec", "recommend", "a", "ask"):
                recommend_tools(parts[1].strip() if len(parts) > 1 else None)
                continue

            if raw_lower in ("q", "quit", "exit"):
                console.print(Panel(
                    "[bold white on magenta]  Goodbye — Come Back Safely  [/bold white on magenta]",
                    box=box.HEAVY, border_style="magenta",
                ))
                break

            try:
                choice = int(raw_lower)
            except ValueError:
                # Natural-language entry: any other text is treated as "what do
                # you want to do?" and routed to AI1 recommend. The prefixes
                # above (/ s r a t) are just accelerators, not required.
                recommend_tools(intent=raw)
                continue

            if 1 <= choice <= len(all_tools):
                title, icon, _ = tool_definitions[choice - 1]
                console.print(Panel(
                    f"[bold magenta]{icon}  {title}[/bold magenta]",
                    border_style="magenta", box=box.ROUNDED,
                ))
                try:
                    all_tools[choice - 1].show_options()
                except Exception as e:  # noqa: BLE001 - REPL UI boundary isolates failing tool plugins
                    console.print(Panel(
                        f"[red]Error while opening {title}[/red]\n{e}",
                        border_style="red",
                    ))
                    ask("[dim]Press Enter to return to main menu[/dim]", default="")
            else:
                console.print(f"[red]⚠  Choose 1–{len(all_tools)}, ? for help, or q to quit.[/red]")
                ask("[dim]Press Enter to continue[/dim]", default="")

        except KeyboardInterrupt:
            console.print("\n[bold red]Interrupted — exiting[/bold red]")
            break


# ── Entry point ────────────────────────────────────────────────────────────────

def _build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="noxentra", add_help=True,
                                description="noxentra headless orchestrator")
    p.add_argument("--engagement", help="engagement name (creates if new)")
    p.add_argument("--targets", help="target, comma-separated targets, or a file path (one per line)")
    p.add_argument("--scope-out", dest="scope_out",
                   help="comma-separated exclusion globs or a file path (merged into engagement)")
    p.add_argument("--pipeline", default=None, help="pipeline to run against the engagement's targets (default: recon)")
    p.add_argument("--report", action="store_true", help="(re)generate the report")
    p.add_argument("--format", dest="report_format", choices=["md", "html", "sarif", "all"],
                   default="md", help="report output format (default: md)")
    p.add_argument("--list-pipelines", dest="list_pipelines", action="store_true",
                   help="list available pipelines and exit")
    p.add_argument("--list-engagements", dest="list_engagements", action="store_true",
                   help="list saved engagements and exit")
    p.add_argument("--ai-summary", dest="ai_summary", action="store_true",
                   help="opt-in local-AI (Ollama) summary of findings")
    p.add_argument("--ai-report", dest="ai_report", action="store_true",
                   help="opt-in AI narrative report draft (report.draft.md; facts stay deterministic)")
    return p


def _load_list_arg(spec: str) -> list[str]:
    p = Path(spec)
    if p.is_file():
        return [ln.strip() for ln in p.read_text().splitlines() if ln.strip()]
    return [part.strip() for part in spec.split(",") if part.strip()]


def _load_targets(spec: str) -> list[str]:
    return _load_list_arg(spec)


def _print_pipelines() -> None:
    for item in orchestrator.list_pipelines():
        desc = f" — {item['description']}" if item["description"] else ""
        console.print(f"[cyan]{item['name']}[/cyan]{desc}")


def _print_engagements() -> None:
    from noxentra.tui import data

    rows = data.engagements()
    if not rows:
        console.print("[dim]No engagements found.[/dim]")
        return
    for r in rows:
        console.print(f"[cyan]{r.name}[/cyan] · {r.targets_count} target(s) · {r.findings_count} finding(s)")


def _run_headless(args) -> None:
    console.print(Panel("[bold yellow]AUTHORIZED TARGETS ONLY[/bold yellow] — "
                        "run only against systems you own or are explicitly permitted to test.",
                        border_style="yellow"))
    targets = _load_targets(args.targets) if args.targets else None
    e = engagement.get_or_create(args.engagement, targets)
    if getattr(args, "scope_out", None):
        merged_out = list(e.scope_out)
        for pat in _load_list_arg(args.scope_out):
            if pat not in merged_out:
                merged_out.append(pat)
        if merged_out != e.scope_out:
            e.scope_out = merged_out
            e.save()

    for t in e.targets:
        if not e.in_scope(t):
            console.print(f"[bold red]WARNING:[/bold red] target [white]{t}[/white] "
                          f"is outside declared scope; proceeding and logging.")
            e.log(f"WARNING out-of-scope target: {t}")

    ran = False
    run_requested = bool(args.targets) or args.pipeline is not None
    if run_requested:
        if not e.targets:
            console.print("[yellow]No targets set for this engagement; pass --targets.[/yellow]")
        else:
            pipeline = args.pipeline or "recon"
            console.print(f"[cyan]Running pipeline '{pipeline}'...[/cyan]")
            with orchestrator.live_progress(console.print):
                result = orchestrator.run_pipeline(e, pipeline)
            new_n = e.runs[-1].get("new_findings") if e.runs else None
            prefix = f"+{new_n} new, " if new_n is not None else ""
            console.print(f"[green]{prefix}{len(result)} total findings ->[/green] {e.findings_file}")
            ran = True

    if ran or args.report:
        fmt = getattr(args, "report_format", "md")
        if fmt in ("md", "all"):
            path = report.generate_report(e)
            console.print(f"[green]Report ->[/green] {path}")
        if fmt in ("html", "all"):
            path = report.generate_html_report(e)
            console.print(f"[green]HTML report ->[/green] {path}")
        if fmt in ("sarif", "all"):
            path = report.generate_sarif_report(e)
            console.print(f"[green]SARIF report ->[/green] {path}")

    if args.ai_summary:
        summary = ai_summary.summarize(e)
        if summary is None:
            console.print("[yellow]No local model reachable (Ollama at :11434) — "
                          "skipping AI summary.[/yellow]")
        else:
            (e.workspace / "summary.md").write_text(summary)
            console.print(f"[green]AI summary ->[/green] {e.workspace / 'summary.md'}")

    if args.ai_report:
        path = ai_report.draft_report(e)
        if path is None:
            console.print("[yellow]No findings to draft, or no model reachable "
                          "(Ollama at :11434 / BYO-key) — skipping AI report.[/yellow]")
        else:
            console.print(f"[green]AI report draft ->[/green] {path} "
                          "[dim](verify before use)[/dim]")


def main():
    argv = sys.argv[1:]
    # `--classic` forces the legacy rich menu; strip it before the headless check
    # below so it doesn't get mistaken for a headless flag.
    force_classic = "--classic" in argv
    argv = [a for a in argv if a != "--classic"]

    # Make --classic / headless honour the readline fallback everywhere — not just
    # the REPL, but every nested tool menu that reads via prompt.read_line/simple.
    from noxentra import prompt
    prompt.FORCE_CLASSIC = force_classic

    if argv:
        # Any argument means headless mode. argparse rejects unknown/typo args with
        # exit 2 (instead of silently opening the menu); -h/--help exits 0.
        parser = _build_arg_parser()
        args = parser.parse_args(argv)
        if args.list_pipelines or args.list_engagements:
            if args.list_pipelines:
                _print_pipelines()
            if args.list_engagements:
                _print_engagements()
            return
        if not args.engagement:
            parser.error("--engagement is required in headless mode")   # prints usage, exits 2
        _run_headless(args)
        return
    try:
        from noxentra.os_detect import CURRENT_OS

        if CURRENT_OS.system == "windows":
            console.print(Panel("[bold red]Please run this tool on Linux or macOS.[/bold red]"))
            try:
                if Confirm.ask("Open guidance link in your browser?", default=True):
                    webbrowser.open_new_tab(f"{REPO_WEB_URL}#windows")
            except (EOFError, KeyboardInterrupt):
                pass
            return

        if CURRENT_OS.system not in ("linux", "macos"):
            console.print(f"[yellow]Unsupported OS: {CURRENT_OS.system}. Proceeding anyway...[/yellow]")

        get_tools_dir()   # ensures ~/.noxentra/tools/ exists
        from noxentra import config
        config.ensure_user_files()   # first run: scaffold config.json + commented .env

        if force_classic:
            from noxentra import repl
            if repl._use_repl(force_classic):
                repl.run_repl()
            else:
                interact_menu()
        elif sys.stdin.isatty() and sys.stdout.isatty():
            from noxentra.tui import app as tui_app
            tui_app.run()
        else:
            interact_menu()

    except KeyboardInterrupt:
        console.print("\n[bold red]Exiting...[/bold red]")


if __name__ == "__main__":
    main()
