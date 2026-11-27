const PIPELINES = [
  { name: "recon", desc: "Passive subdomain discovery -> live HTTP probe -> vulnerability scan", chain: "subfinder -> httpx -> nuclei", target: "example.com" },
  { name: "full_recon", desc: "Port/service scan -> subdomain discovery -> live probe -> vuln scan", chain: "nmap -> subfinder -> httpx -> nuclei", target: "example.com" },
  { name: "dns_enum", desc: "Passive subdomain enum -> DNS record resolution -> HTTP probe", chain: "subfinder -> dnsx -> httpx", target: "example.com" },
  { name: "web_enum", desc: "Probe live web URLs -> parallel directory brute-force", chain: "httpx -> gobuster", target: "https://app.example.com" },
  { name: "web_deep", desc: "Probe live URLs -> tech fingerprint -> parallel content fuzzing", chain: "httpx -> whatweb -> ffuf", target: "https://app.example.com" },
  { name: "passive_urls", desc: "Passive archive URLs -> live HTTP probe -> vulnerability scan", chain: "gau -> httpx -> nuclei", target: "example.com" },
  { name: "tls_recon", desc: "Subdomain enum -> TLS cert/SAN inspection -> HTTP probe", chain: "subfinder -> tlsx -> httpx", target: "example.com" },
  { name: "cloud_scan", desc: "Filesystem / IaC vulnerability scan -> SBOM/vuln cross-check", chain: "trivy fs -> grype", target: "." },
  { name: "container_scan", desc: "Container image vulnerability scan -> SBOM cross-check", chain: "trivy image -> grype", target: "alpine:3.19" },
  { name: "iac_scan", desc: "IaC policy & misconfiguration scan -> filesystem vuln check", chain: "terrascan -> trivy fs", target: "./terraform" },
  { name: "k8s_scan", desc: "Passive Kubernetes cluster penetration scan", chain: "kube-hunter", target: "10.0.0.10" },
];

let selected = "full_recon";
const grid = document.getElementById("pipe-grid");
const eng = document.getElementById("eng");
const tgt = document.getElementById("tgt");
const scp = document.getElementById("scp");
const fmt = document.getElementById("fmt");
const out = document.getElementById("cli-out");
const copyBtn = document.getElementById("copy-cli");

function updateCmd() {
  const s = scp.value.trim() ? ` --scope-out ${scp.value.trim()}` : "";
  out.textContent = `noxentra --engagement ${eng.value.trim() || "acme"} --targets ${tgt.value.trim() || "example.com"}${s} --pipeline ${selected} --report --format ${fmt.value}`;
}

function renderCards() {
  grid.innerHTML = PIPELINES.map((p) => `
    <article class="pipe-card ${p.name === selected ? "selected" : ""}" data-name="${p.name}">
      <div class="pipe-name">${p.name}</div>
      <p class="pipe-desc">${p.desc}</p>
      <div class="pipe-steps">${p.chain}</div>
    </article>
  `).join("");
}

grid.addEventListener("click", (e) => {
  const card = e.target.closest("[data-name]");
  if (!card) return;
  selected = card.getAttribute("data-name");
  const p = PIPELINES.find((x) => x.name === selected);
  if (p) tgt.value = p.target;
  renderCards();
  updateCmd();
});

[eng, tgt, scp, fmt].forEach((el) => el.addEventListener("input", updateCmd));
copyBtn.addEventListener("click", async () => {
  try {
    await navigator.clipboard.writeText(out.textContent);
    copyBtn.textContent = "copied";
    setTimeout(() => { copyBtn.textContent = "copy"; }, 1400);
  } catch {}
});

const params = new URLSearchParams(location.search);
const requestedPipe = params.get("pipeline");
if (requestedPipe) {
  const match = PIPELINES.find((x) => x.name === requestedPipe);
  if (match) {
    selected = match.name;
    tgt.value = match.target;
  }
}

renderCards();
updateCmd();
