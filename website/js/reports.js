const PREVIEWS = {
      md: `# Engagement: acme

- **Targets:** ./terraform, 10.0.0.5
- **Scope out:** admin.example.com
- **Total findings:** 3

## Misconfigurations (1)

| Severity | Name | Target | Tool |
|---|---|---|---|
| high | AC_AWS_0207: s3BucketEncryption | main.tf:12 | terrascan |

## Vulnerabilities (1)

| Severity | Name | Target | Tool |
|---|---|---|---|
| medium | Kubelet API Read-Only Port | 10.0.0.5:10255 | kube-hunter |`,
      sarif: `{
  "version": "2.1.0",
  "$schema": "https://json.schemastore.org/sarif-2.1.0.json",
  "runs": [{
    "tool": { "driver": { "name": "Noxentra", "version": "3.1.0" } },
    "results": [{
      "ruleId": "AC_AWS_0207",
      "level": "error",
      "message": { "text": "AC_AWS_0207: s3BucketEncryption" },
      "locations": [{ "physicalLocation": { "artifactLocation": { "uri": "main.tf:12" } } }]
    }]
  }]
}`,
      ci: `- name: Run Noxentra IaC Scan
  run: |
    noxentra --engagement ci --targets ./terraform --pipeline iac_scan --report --format sarif

- name: Upload SARIF to GitHub Security
  uses: github/codeql-action/upload-sarif@v3
  with:
    sarif_file: ~/.noxentra/engagements/ci/report.sarif.json`,
    };
    const fBtns = Array.from(document.querySelectorAll(".fmt-btn"));
    const prev = document.getElementById("fmt-preview");
    fBtns.forEach((b) => b.addEventListener("click", () => {
      const txt = PREVIEWS[b.getAttribute("data-fmt")];
      if (!txt) return;
      fBtns.forEach((x) => x.setAttribute("aria-pressed", String(x === b)));
      prev.textContent = txt;
    }));
