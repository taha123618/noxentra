const copyBtn = document.getElementById("copy-btn");
const installCmd = document.getElementById("install-cmd");
copyBtn.addEventListener("click", async () => {
  try {
    await navigator.clipboard.writeText(installCmd.textContent.trim());
    copyBtn.textContent = "copied";
    setTimeout(() => { copyBtn.textContent = "copy"; }, 1400);
  } catch { }
});

const tabs = Array.from(document.querySelectorAll('[role="tab"]'));
const panels = Array.from(document.querySelectorAll('[role="tabpanel"]'));
function setTab(tab) {
  tabs.forEach((t) => t.setAttribute("aria-selected", String(t === tab)));
  let activePanel = null;
  panels.forEach((p) => {
    const on = p.id === tab.getAttribute("aria-controls");
    p.classList.toggle("active", on);
    if (on) activePanel = p;
  });
  if (activePanel && typeof gsap !== "undefined" && !window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
    gsap.fromTo(activePanel.querySelectorAll(".ln"),
      { opacity: 0, y: 5 },
      { opacity: 1, y: 0, duration: 0.22, stagger: 0.025, ease: "power2.out", clearProps: "transform" }
    );
  }
}
tabs.forEach((tab, i) => {
  tab.addEventListener("click", () => setTab(tab));
  tab.addEventListener("keydown", (e) => {
    if (e.key === "ArrowRight") {
      const n = tabs[(i + 1) % tabs.length]; n.focus(); setTab(n);
    } else if (e.key === "ArrowLeft") {
      const p = tabs[(i - 1 + tabs.length) % tabs.length]; p.focus(); setTab(p);
    }
  });
});

const SHOTS = {
  1: {
    src: "assets/screenshots/1.png",
    alt: "Noxentra interactive console showing categories and live search",
    cap: "Main console: 21 tool categories, live search across 306 active tools, and `/` command palette.",
  },
  2: {
    src: "assets/screenshots/2.png",
    alt: "Noxentra /tags view showing 64 canonical tags and counts",
    cap: "`/tags` — 64 canonical taxonomy tags with live tool counts.",
  },
  3: {
    src: "assets/screenshots/3.png",
    alt: "Noxentra /ai view for plain-English task recommendation",
    cap: "`/ai` — pick a common task or describe what you need in plain English.",
  },
  4: {
    src: "assets/screenshots/4.png",
    alt: "Noxentra tool detail card with install, run, and usage cheatsheet",
    cap: "Tool card — install command, run action, and curated usage cheatsheet.",
  },
};
const shotBtns = Array.from(document.querySelectorAll(".shot-btn"));
const shotImg = document.getElementById("shot-img");
const shotCap = document.getElementById("shot-cap");
shotBtns.forEach((btn) => {
  btn.addEventListener("click", () => {
    const s = SHOTS[btn.getAttribute("data-shot")];
    if (!s) return;
    shotBtns.forEach((b) => b.setAttribute("aria-pressed", String(b === btn)));
    shotImg.src = s.src;
    shotImg.alt = s.alt;
    shotCap.textContent = s.cap;
    if (typeof gsap !== "undefined" && !window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      gsap.fromTo(shotImg, { opacity: 0.35 }, { opacity: 1, duration: 0.25, ease: "power1.out" });
    }
  });
});

const pipeCmd = document.getElementById("pipe-cmd");
const pipeCopy = document.getElementById("pipe-copy");
const pipeRows = Array.from(document.querySelectorAll("#pipe-table tbody tr"));
pipeRows.forEach((row) => {
  row.addEventListener("click", () => {
    const name = row.getAttribute("data-pipe");
    const target = row.getAttribute("data-target");
    pipeRows.forEach((r) => { r.style.background = r === row ? "#141418" : ""; });
    pipeCmd.textContent = `noxentra --engagement acme --targets ${target} --pipeline ${name} --report --format all`;
  });
});
pipeCopy.addEventListener("click", async () => {
  try {
    await navigator.clipboard.writeText(pipeCmd.textContent.trim());
    pipeCopy.textContent = "copied";
    setTimeout(() => { pipeCopy.textContent = "copy"; }, 1400);
  } catch { }
});

(() => {
  const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  if (reduced || typeof gsap === "undefined") return;

  if (typeof ScrollTrigger !== "undefined") {
    gsap.registerPlugin(ScrollTrigger);
  }

  if (typeof Lenis !== "undefined") {
    const lenis = new Lenis({
      duration: 1.05,
      easing: (t) => Math.min(1, 1.001 - Math.pow(2, -10 * t)),
      smoothWheel: true,
    });
    window.__noxentraLenis = lenis;
    if (typeof ScrollTrigger !== "undefined") {
      lenis.on("scroll", ScrollTrigger.update);
      gsap.ticker.add((time) => lenis.raf(time * 1000));
      gsap.ticker.lagSmoothing(0);
    } else {
      function raf(time) { lenis.raf(time); requestAnimationFrame(raf); }
      requestAnimationFrame(raf);
    }
  }

  // Hero entrance stagger
  gsap.from(".hero .meta-line, .hero h1, .hero .hero-copy, .hero .install-row, .hero .hero-links, .hero .term", {
    y: 16,
    opacity: 0,
    duration: 0.65,
    stagger: 0.06,
    ease: "power3.out",
    clearProps: "transform",
  });

  if (typeof ScrollTrigger !== "undefined") {
    gsap.from("#interface .shot-frame", {
      y: 22,
      opacity: 0,
      duration: 0.65,
      ease: "power2.out",
      clearProps: "transform",
      scrollTrigger: { trigger: "#interface", start: "top 82%", once: true },
    });

    gsap.from("#architecture .cell", {
      y: 16,
      opacity: 0,
      duration: 0.5,
      stagger: 0.06,
      ease: "power2.out",
      clearProps: "transform",
      scrollTrigger: { trigger: "#architecture .matrix", start: "top 84%", once: true },
    });

    gsap.from("#pipelines tbody tr", {
      y: 10,
      opacity: 0,
      duration: 0.4,
      stagger: 0.03,
      ease: "power2.out",
      clearProps: "transform",
      scrollTrigger: { trigger: "#pipe-table", start: "top 85%", once: true },
    });
  }
})();
