"""Single source of truth for Noxentra's assembled tool catalog and tag index."""
import noxentra.registry as _registry
from noxentra.constants import USER_CONFIG_DIR
from noxentra.core import Noxentra, NoxentraCollection
from noxentra.tools.active_directory import ActiveDirectoryTools
from noxentra.tools.anonsurf import AnonSurfTools
from noxentra.tools.cloud_security import CloudSecurityTools
from noxentra.tools.ddos import DDOSTools
from noxentra.tools.exploit_frameworks import ExploitFrameworkTools
from noxentra.tools.forensics import ForensicTools
from noxentra.tools.information_gathering import InformationGatheringTools
from noxentra.tools.mobile_security import MobileSecurityTools
from noxentra.tools.other_tools import OtherTools
from noxentra.tools.payload_creator import PayloadCreatorTools
from noxentra.tools.phishing_attack import PhishingAttackTools
from noxentra.tools.post_exploitation import PostExploitationTools
from noxentra.tools.remote_administration import RemoteAdministrationTools
from noxentra.tools.reverse_engineering import ReverseEngineeringTools
from noxentra.tools.sql_injection import SqlInjectionTools
from noxentra.tools.steganography import SteganographyTools
from noxentra.tools.tool_manager import ToolManager
from noxentra.tools.web_attack import WebAttackTools
from noxentra.tools.wireless_attack import WirelessAttackTools
from noxentra.tools.wordlist_generator import WordlistGeneratorTools
from noxentra.tools.xss_attack import XSSAttackTools

# (full_title, icon, menu_label)
tool_definitions: list[tuple[str, str, str]] = [
    ("Anonymously Hiding Tools",         "🛡 ", "Anonymously Hiding"),
    ("Information gathering tools",      "🔍",  "Information Gathering"),
    ("Wordlist Generator",               "📚",  "Wordlist Generator"),
    ("Wireless attack tools",            "📶",  "Wireless Attack"),
    ("SQL Injection Tools",              "🧩",  "SQL Injection"),
    ("Phishing attack tools",            "🎣",  "Phishing Attack"),
    ("Web Attack tools",                 "🌐",  "Web Attack"),
    ("Post exploitation tools",          "🔧",  "Post Exploitation"),
    ("Forensic tools",                   "🕵 ", "Forensics"),
    ("Payload creation tools",           "📦",  "Payload Creation"),
    ("Exploit framework",                "🧰",  "Exploit Framework"),
    ("Reverse engineering tools",        "🔁",  "Reverse Engineering"),
    ("DDOS Attack Tools",                "⚡",  "DDOS Attack"),
    ("Remote Administrator Tools (RAT)", "🖥 ", "Remote Admin (RAT)"),
    ("XSS Attack Tools",                 "💥",  "XSS Attack"),
    ("Steganography tools",              "🖼 ", "Steganography"),
    ("Active Directory Tools",           "🏢",  "Active Directory"),
    ("Cloud Security Tools",             "☁ ",  "Cloud Security"),
    ("Mobile Security Tools",            "📱",  "Mobile Security"),
    ("Other tools",                      "✨",  "Other Tools"),
    ("Update or Uninstall | Noxentra",   "♻ ",  "Update / Uninstall"),
]

all_tools: list[NoxentraCollection] = [
    AnonSurfTools(),
    InformationGatheringTools(),
    WordlistGeneratorTools(),
    WirelessAttackTools(),
    SqlInjectionTools(),
    PhishingAttackTools(),
    WebAttackTools(),
    PostExploitationTools(),
    ForensicTools(),
    PayloadCreatorTools(),
    ExploitFrameworkTools(),
    ReverseEngineeringTools(),
    DDOSTools(),
    RemoteAdministrationTools(),
    XSSAttackTools(),
    SteganographyTools(),
    ActiveDirectoryTools(),
    CloudSecurityTools(),
    MobileSecurityTools(),
    OtherTools(),
    ToolManager(),
]

_reg = _registry.load(user_dir=USER_CONFIG_DIR)
for _coll in all_tools:
    _extra = _reg.merge_tools_for(_coll.TITLE)
    if _extra:
        _coll.TOOLS = list(_coll.TOOLS) + _extra

_insert_at = len(all_tools) - 1   # keep ToolManager (last) at the end
all_tools[_insert_at:_insert_at] = _reg.new_collections
tool_definitions[_insert_at:_insert_at] = _reg.new_definitions


class AllTools(NoxentraCollection):
    TITLE = "All tools"
    TOOLS = all_tools


def collect_all_tools() -> list[tuple]:
    """Walk all collections and return (tool_instance, category_name) pairs."""
    results = []

    def _walk(items, parent_title=""):
        for item in items:
            if isinstance(item, NoxentraCollection):
                _walk(item.TOOLS, item.TITLE)
            elif isinstance(item, Noxentra):
                results.append((item, parent_title))

    _walk(all_tools)
    return results


def get_all_tags() -> dict[str, list[tuple]]:
    """Build tag -> [(tool, category)] index from each tool's curated ``.TAGS``."""
    tag_index: dict[str, list[tuple]] = {}
    for tool, cat in collect_all_tools():
        for t in getattr(tool, "TAGS", []) or []:
            tag_index.setdefault(t, []).append((tool, cat))
    return tag_index


RECOMMENDATIONS: dict[str, list[str]] = {
    "scan a network":           ["scanner", "port-scan"],
    "find subdomains":          ["recon"],
    "scan for vulnerabilities": ["scanner", "web"],
    "crack passwords":          ["bruteforce", "credentials"],
    "find leaked secrets":      ["credentials"],
    "phishing campaign":        ["social-engineering"],
    "post exploitation":        ["c2", "privesc"],
    "pivot through network":    ["network"],
    "pentest active directory": ["active-directory"],
    "pentest web application":  ["web", "scanner"],
    "pentest cloud":            ["cloud"],
    "pentest mobile app":       ["mobile"],
    "reverse engineer binary":  ["reversing"],
    "capture wifi handshake":   ["wireless"],
    "intercept http traffic":   ["web", "network"],
    "forensic analysis":        ["forensics"],
    "ddos testing":             ["ddos"],
    "create payloads":          ["payload"],
    "find xss vulnerabilities": ["web"],
    "brute force directories":  ["bruteforce", "web"],
    "osint / recon a target":   ["osint", "recon"],
    "hide my identity":         ["network"],
}

_reg.apply_overlays(collect_all_tools())
