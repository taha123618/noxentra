document.querySelectorAll("[data-copy]").forEach((btn) => {
  btn.addEventListener("click", async () => {
    const pre = btn.closest(".code-wrap")?.querySelector("pre");
    if (!pre) return;
    try {
      await navigator.clipboard.writeText(pre.textContent.trim());
      const prev = btn.textContent;
      btn.textContent = "Copied!";
      setTimeout(() => { btn.textContent = prev; }, 1500);
    } catch {}
  });
});

const sideLinks = Array.from(document.querySelectorAll(".sidebar a"));
const sections = Array.from(document.querySelectorAll(".doc-section"));
const obs = new IntersectionObserver((entries) => {
  const visible = entries.find((e) => e.isIntersecting);
  if (!visible) return;
  sideLinks.forEach((a) => {
    const active = a.getAttribute("href") === `#${visible.target.id}`;
    a.style.color = active ? "#fafafa" : "";
    a.style.background = active ? "#18181b" : "";
  });
}, { rootMargin: "-20% 0px -65% 0px" });
sections.forEach((s) => obs.observe(s));
