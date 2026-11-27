const WF = {
  goal: {
    title: "/goal — Step-by-step objective planner",
    desc: "Calls the configured model once to draft a concrete plan, asks for target authorization, and pauses before every command.",
    points: [
      "Workspace saved under ~/.noxentra/goals/ with plan.json and run.log",
      "Every step runs list-form (shell=False)",
      "Degrades to tool recommendations if no model is configured",
    ],
    term: `noxentra > /goal audit terraform and kubernetes manifests\n\nScope confirmation required for: ./infra\n[1] terrascan scan -i terraform -d ./infra\n[2] trivy fs --quiet ./infra\n\nRun step 1? [y] run · [e] edit · [s] skip · [q] abort`,
  },
  ai: {
    title: "/ai — Taxonomy-grounded recommender",
    desc: "Maps plain-English intent strictly onto the 64 canonical tags in tags.py so non-existent tools can never be hallucinated.",
    points: [
      "Offline keyword fallback answers immediately without an API key",
      "Returns curated tools + exact documented usage cheatsheets",
      "Works inline in TUI or by typing plain text in --classic",
    ],
    term: `noxentra > /ai check aws iam policies for privilege escalation\n\nMatched tags: [cloud, scanner, enumeration]\n  1. Cloudsplaining (AWS IAM Analyzer)\n  2. Prowler (Cloud Security Scanner)\n  3. Pacu (AWS Exploitation Framework)`,
  },
  find: {
    title: "/find — Suggest-only catalog & GitHub search",
    desc: "Searches the 294 curated catalog tools first, then queries the GitHub API with zero model calls and zero auto-install.",
    points: [
      "Ranks active, trusted-owner repositories from catalog_owners.py",
      "Refuses out-of-scope requests (DoS, jamming, malware) before network calls",
      "Saves bookmarks to ~/.noxentra/found.yaml without run commands",
    ],
    term: `noxentra > /find rust tcp reverse tunnel\n\nIn your catalog (vetted)\n  • bore (Modern Rust TCP Tunnel)  [tunneling, network]\n\nFound on GitHub (suggest-only)\n  • ekzhang/bore  8.4k★ · active · trusted owner`,
  },
  config: {
    title: "/config — Local-first model & token settings",
    desc: "Supports any OpenAI-compatible endpoint or local Ollama instance, storing secrets solely in ~/.noxentra/.env (mode 0600).",
    points: [
      "/config test probes the configured provider and reports exact status",
      "GitHub token (no-scope) raises /find rate limit from 10 to 30 req/min",
      "All non-secret settings live in ~/.noxentra/config.json",
    ],
    term: `noxentra > /config ai_base_url http://127.0.0.1:11434/v1\nnoxentra > /config ai_model qwen2.5-coder:7b\nnoxentra > /config test\n\n✓ Connected to local Ollama (qwen2.5-coder:7b)`,
  },
};
const btns = Array.from(document.querySelectorAll(".wf-btn"));
const tEl = document.getElementById("wf-title");
const dEl = document.getElementById("wf-desc");
const pEl = document.getElementById("wf-points");
const termEl = document.getElementById("wf-term");
btns.forEach((b) => b.addEventListener("click", () => {
  const item = WF[b.getAttribute("data-wf")];
  if (!item) return;
  btns.forEach((x) => x.setAttribute("aria-pressed", String(x === b)));
  tEl.textContent = item.title;
  dEl.textContent = item.desc;
  pEl.innerHTML = item.points.map((pt) => `<li>${pt}</li>`).join("");
  termEl.textContent = item.term;
}));
