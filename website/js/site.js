(() => {
  const NAV_LINKS = [
    { label: "Home", desc: "Overview & demo", href: "index.html" },
    { label: "Catalog", desc: "294 tools · 21 categories", href: "catalog.html" },
    { label: "Pipelines", desc: "11 headless workflows", href: "pipelines.html" },
    { label: "Workflows", desc: "/goal, /ai, /find, /config", href: "workflows.html" },
    { label: "Reports", desc: "MD, HTML, SARIF v2.1.0", href: "reports.html" },
    { label: "Safety", desc: "Trust & scope invariants", href: "safety.html" },
    { label: "Docs", desc: "Install & CLI reference", href: "docs.html" },
  ];

  const current = (location.pathname.split("/").pop() || "index.html").toLowerCase();

  const headerEl = document.getElementById("site-header");
  if (headerEl) {
    headerEl.innerHTML = `
      <div class="nav">
        <a class="logo" href="index.html">
          <img src="assets/logo.png" alt="Noxentra logo" />
          <span class="logo-text">
            <span class="logo-name">NOXENTRA</span>
            <span class="logo-tag">AI-Guided Reconnaissance &amp; Security Framework</span>
          </span>
        </a>
        <nav class="nav-links" aria-label="Primary">
          ${NAV_LINKS.map((l) => `<a href="${l.href}" class="${current === l.href ? "active" : ""}">${l.label}</a>`).join("")}
        </nav>
        <div class="nav-right">
          <button class="cmdk-trigger" type="button" data-cmdk-open aria-label="Search tools, pipelines, and docs">
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/></svg>
            <span class="cmdk-label">Search</span>
            <span class="cmdk-kbd">⌘K</span>
          </button>
          <a class="gh-star" href="https://github.com/taha123618/noxentra" target="_blank" rel="noopener noreferrer" aria-label="Star Noxentra on GitHub">
            <svg width="13" height="13" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z"/></svg>
            <span>Star</span>
          </a>
          <button class="menu-btn" type="button" id="mobile-menu-btn" aria-expanded="false" aria-controls="mobile-nav" aria-label="Toggle navigation menu">
            <span class="hb-line" aria-hidden="true"></span>
            <span class="hb-line" aria-hidden="true"></span>
            <span class="hb-line" aria-hidden="true"></span>
          </button>
        </div>
      </div>
      <nav class="mobile-nav" id="mobile-nav" aria-label="Mobile navigation">
        <div class="mobile-nav-body">
          <button class="mobile-search-btn" type="button" data-cmdk-open>
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/></svg>
            <span>Search 294 tools, pipelines, docs…</span>
          </button>
          <div class="mobile-nav-links">
            ${NAV_LINKS.map((l) => `
              <a href="${l.href}" class="${current === l.href ? "active" : ""}">
                <span class="m-link-main">
                  <span class="m-link-title">${l.label}</span>
                  <span class="m-link-desc">${l.desc}</span>
                </span>
                <span class="m-link-arr">→</span>
              </a>
            `).join("")}
          </div>
        </div>
        <div class="mobile-nav-foot">
          <a class="mobile-gh-cta" href="https://github.com/taha123618/noxentra" target="_blank" rel="noopener noreferrer">
            <span>★ Star Noxentra on GitHub</span>
            <span>↗</span>
          </a>
          <div class="mobile-meta">MIT License · Local-first</div>
        </div>
      </nav>
    `;
    const mBtn = document.getElementById("mobile-menu-btn");
    const mNav = document.getElementById("mobile-nav");
    if (mBtn && mNav) {
      const setMobileNav = (open) => {
        mNav.classList.toggle("open", open);
        mBtn.setAttribute("aria-expanded", String(open));
        document.body.style.overflow = open ? "hidden" : "";
      };
      mBtn.addEventListener("click", () => setMobileNav(!mNav.classList.contains("open")));
      mNav.querySelectorAll("a, [data-cmdk-open]").forEach((el) => el.addEventListener("click", () => setMobileNav(false)));
      document.addEventListener("keydown", (e) => {
        if (e.key === "Escape" && mNav.classList.contains("open")) setMobileNav(false);
      });
    }
  }

  const footerEl = document.getElementById("site-footer");
  if (footerEl) {
    footerEl.innerHTML = `
      <div class="foot">
        <div>NOXENTRA · MIT License · Authorized security testing and owned infrastructure only.</div>
        <div class="foot-links">
          <a href="index.html">Home</a>
          <a href="catalog.html">Catalog</a>
          <a href="pipelines.html">Pipelines</a>
          <a href="workflows.html">Workflows</a>
          <a href="reports.html">Reports</a>
          <a href="safety.html">Safety</a>
          <a href="docs.html">Docs</a>
        </div>
      </div>
    `;
  }

  const PAGES = [
    { group: "Pages", label: "Home", hint: "Overview & interactive demo", href: "index.html" },
    { group: "Pages", label: "Tool Catalog (294)", hint: "21 categories · 64 tags", href: "catalog.html" },
    { group: "Pages", label: "Headless Pipelines (11)", hint: "17 normalized parsers", href: "pipelines.html" },
    { group: "Pages", label: "AI Workflows", hint: "/goal, /ai, /find, /config", href: "workflows.html" },
    { group: "Pages", label: "Reports & SARIF Exports", hint: "MD, HTML, SARIF v2.1.0", href: "reports.html" },
    { group: "Pages", label: "Security & Trust Architecture", hint: "Invariants & scope safety", href: "safety.html" },
    { group: "Pages", label: "Documentation", hint: "Install, CLI & guides", href: "docs.html" },
    { group: "Pages", label: "Installation (pipx / uv)", hint: "docs.html#installation", href: "docs.html#installation" },
  ];

  const style = document.createElement("style");
  style.textContent = `
    .cmdk-trigger{display:inline-flex;align-items:center;gap:8px;padding:5px 10px;border-radius:6px;border:1px solid #27272a;background:#111114;color:#a1a1aa;font-family:"JetBrains Mono",monospace;font-size:.76rem;cursor:pointer;transition:border-color .15s,color .15s}
    .cmdk-trigger:hover{border-color:#3f3f46;color:#fafafa}
    .cmdk-kbd{padding:1px 5px;border-radius:4px;background:#18181b;border:1px solid #27272a;color:#71717a;font-size:.7rem}
    .cmdk-backdrop{position:fixed;inset:0;background:rgba(0,0,0,.72);backdrop-filter:blur(4px);display:none;align-items:flex-start;justify-content:center;padding-top:12vh;z-index:100}
    .cmdk-backdrop.open{display:flex}
    .cmdk-modal{width:min(620px,94vw);background:#111114;border:1px solid #3f3f46;border-radius:10px;overflow:hidden;box-shadow:0 24px 64px rgba(0,0,0,.75)}
    .cmdk-top{display:flex;align-items:center;border-bottom:1px solid #27272a;padding-right:12px}
    .cmdk-input{flex:1;padding:14px 16px;background:#111114;border:none;color:#fafafa;font-family:"Inter",sans-serif;font-size:.95rem;outline:none}
    .cmdk-count{font-family:"JetBrains Mono",monospace;font-size:.72rem;color:#71717a;white-space:nowrap}
    .cmdk-list{max-height:380px;overflow-y:auto;padding:6px}
    .cmdk-group{padding:8px 10px 4px;font-family:"JetBrains Mono",monospace;font-size:.68rem;text-transform:uppercase;letter-spacing:.06em;color:#71717a}
    .cmdk-item{display:flex;justify-content:space-between;align-items:center;gap:12px;padding:9px 12px;border-radius:6px;cursor:pointer;font-size:.87rem;color:#e4e4e7}
    .cmdk-item[aria-selected="true"],.cmdk-item:hover{background:#18181b;color:#ffffff}
    .cmdk-item mark{background:rgba(34,197,94,.2);color:#22c55e;border-radius:3px;padding:0 2px}
    .cmdk-hint{font-family:"JetBrains Mono",monospace;font-size:.72rem;color:#71717a;text-align:right;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:45%}
    .cmdk-foot{display:flex;justify-content:space-between;padding:8px 14px;border-top:1px solid #27272a;background:#0d0d10;font-family:"JetBrains Mono",monospace;font-size:.7rem;color:#71717a}
  `;
  document.head.appendChild(style);

  const backdrop = document.createElement("div");
  backdrop.className = "cmdk-backdrop";
  backdrop.innerHTML = `
    <div class="cmdk-modal" role="dialog" aria-modal="true" aria-label="Search Noxentra">
      <div class="cmdk-top">
        <input class="cmdk-input" type="search" placeholder="Search 294 tools (e.g. nmap, nuclei, terrascan), pipelines, or docs..." aria-label="Search commands and tools" />
        <span class="cmdk-count" id="cmdk-count"></span>
      </div>
      <div class="cmdk-list" role="listbox"></div>
      <div class="cmdk-foot">
        <span>↑↓ navigate · ⏎ open</span>
        <span>esc close</span>
      </div>
    </div>
  `;
  document.body.appendChild(backdrop);

  const input = backdrop.querySelector(".cmdk-input");
  const list = backdrop.querySelector(".cmdk-list");
  const countEl = backdrop.querySelector("#cmdk-count");
  let activeIdx = 0;
  let visible = [];
  let indexLoaded = Boolean(window.NOXENTRA_SEARCH);

  function ensureIndex() {
    if (indexLoaded || window.NOXENTRA_SEARCH) {
      indexLoaded = true;
      return;
    }
    indexLoaded = true;
    const s = document.createElement("script");
    s.src = "js/search-index.js";
    s.onload = () => { if (backdrop.classList.contains("open")) render(); };
    document.head.appendChild(s);
  }

  function esc(s) {
    return String(s).replace(/[&<>"']/g, (ch) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[ch]));
  }

  function highlight(text, q) {
    const safe = esc(text);
    if (!q) return safe;
    const idx = text.toLowerCase().indexOf(q);
    if (idx === -1) return safe;
    return esc(text.slice(0, idx)) + `<mark>${esc(text.slice(idx, idx + q.length))}</mark>` + esc(text.slice(idx + q.length));
  }

  function getMatches(q) {
    if (!q) return PAGES;
    const data = window.NOXENTRA_SEARCH || { tools: [], pipelines: [] };
    const tools = [];
    for (const t of data.tools) {
      const titleLow = t.t.toLowerCase();
      const tagsStr = t.g.join(", ");
      const hay = `${titleLow} ${t.c.toLowerCase()} ${tagsStr.toLowerCase()}`;
      if (!hay.includes(q)) continue;
      const score = titleLow.startsWith(q) ? 0 : titleLow.includes(q) ? 1 : 2;
      tools.push({
        score,
        group: "Tools",
        label: t.t,
        hint: t.c,
        href: `catalog.html?q=${encodeURIComponent(t.t)}`,
      });
    }
    tools.sort((a, b) => a.score - b.score || a.label.localeCompare(b.label));

    const pipes = data.pipelines
      .filter((p) => `${p.n} ${p.d}`.toLowerCase().includes(q))
      .map((p) => ({
        group: "Pipelines",
        label: p.n,
        hint: p.d,
        href: `pipelines.html?pipeline=${encodeURIComponent(p.n)}`,
      }));

    const pages = PAGES.filter((p) => `${p.label} ${p.hint}`.toLowerCase().includes(q));
    return [...tools.slice(0, 14), ...pipes.slice(0, 6), ...pages.slice(0, 6)];
  }

  function render() {
    const q = input.value.trim().toLowerCase();
    visible = getMatches(q);
    activeIdx = Math.min(activeIdx, Math.max(0, visible.length - 1));
    countEl.textContent = q ? `${visible.length} result${visible.length === 1 ? "" : "s"}` : "294 tools · 11 pipelines";

    if (!visible.length) {
      list.innerHTML = `<div class="cmdk-item"><span class="cmdk-hint">No matching tools, pipelines, or docs</span></div>`;
      return;
    }

    let lastGroup = "";
    const html = [];
    visible.forEach((item, idx) => {
      if (item.group !== lastGroup) {
        lastGroup = item.group;
        html.push(`<div class="cmdk-group">${esc(lastGroup)}</div>`);
      }
      html.push(`
        <div class="cmdk-item" role="option" aria-selected="${idx === activeIdx}" data-href="${esc(item.href)}">
          <span>${highlight(item.label, q)}</span>
          <span class="cmdk-hint">${esc(item.hint)}</span>
        </div>
      `);
    });
    list.innerHTML = html.join("");
    const activeEl = list.querySelector('[aria-selected="true"]');
    if (activeEl) activeEl.scrollIntoView({ block: "nearest" });
  }

  function openPalette() {
    ensureIndex();
    backdrop.classList.add("open");
    input.value = "";
    activeIdx = 0;
    render();
    input.focus();
  }

  function closePalette() {
    backdrop.classList.remove("open");
  }

  document.querySelectorAll("[data-cmdk-open]").forEach((el) => el.addEventListener("click", openPalette));
  backdrop.addEventListener("click", (e) => { if (e.target === backdrop) closePalette(); });
  list.addEventListener("click", (e) => {
    const row = e.target.closest("[data-href]");
    if (row) window.location.href = row.getAttribute("data-href");
  });

  input.addEventListener("input", () => { activeIdx = 0; render(); });
  input.addEventListener("keydown", (e) => {
    if (e.key === "Escape") return closePalette();
    if (e.key === "ArrowDown" && visible.length) { e.preventDefault(); activeIdx = (activeIdx + 1) % visible.length; render(); }
    if (e.key === "ArrowUp" && visible.length) { e.preventDefault(); activeIdx = (activeIdx - 1 + visible.length) % visible.length; render(); }
    if (e.key === "Enter" && visible[activeIdx]) { window.location.href = visible[activeIdx].href; }
  });

  document.addEventListener("keydown", (e) => {
    const tag = (document.activeElement?.tagName || "").toLowerCase();
    const typing = tag === "input" || tag === "textarea" || tag === "select";
    if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
      e.preventDefault();
      backdrop.classList.contains("open") ? closePalette() : openPalette();
    } else if (e.key === "/" && !typing && !backdrop.classList.contains("open")) {
      e.preventDefault();
      openPalette();
    }
  });

  const topBtn = document.createElement("button");
  topBtn.id = "scroll-top-btn";
  topBtn.type = "button";
  topBtn.setAttribute("aria-label", "Scroll to top");
  topBtn.innerHTML = `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="m18 15-6-6-6 6"/></svg>`;
  document.body.appendChild(topBtn);

  const toggleTopBtn = () => {
    topBtn.classList.toggle("visible", window.scrollY > 320);
  };
  window.addEventListener("scroll", toggleTopBtn, { passive: true });
  toggleTopBtn();

  topBtn.addEventListener("click", () => {
    if (window.__noxentraLenis && typeof window.__noxentraLenis.scrollTo === "function") {
      window.__noxentraLenis.scrollTo(0);
    } else {
      window.scrollTo({ top: 0, behavior: "smooth" });
    }
  });
})();
