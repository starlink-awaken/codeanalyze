# Security Policy

## Supported Versions

| Version | Supported          |
|---------|-------------------|
| 0.2.x   | ✅ Active          |
| 0.1.x   | ❌ End of life     |

## Reporting a Vulnerability

codeanalyze reads files from user-specified paths and may execute
external binaries (`pdftotext`, optionally `libreoffice`). While the
codebase has undergone two rounds of adversarial red-teaming, no
security guarantees are made for alpha-stage software.

**To report a vulnerability:**

1. **DO NOT** open a public GitHub issue
2. Email: `security@workspace.local` (placeholder — configure for your repo)
3. Include:
   - Affected version and file/line
   - Proof of concept or reproduction steps
   - Impact assessment

You should receive a response within 48 hours.

## Known Security Controls

- All CLI paths validated against `Path.home()` — directory traversal blocked
- Cypher export escapes both `\` and `'` — injection prevented
- XML parsing uses `defusedxml` or disables external entities — XXE blocked
- ZIP parsing enforces 10MB per-entry limit — ZIP bomb mitigated
- PDF parsing has 60s timeout — long-running processes logged
- All `except` blocks log failures — no silent error swallowing
- Control characters stripped from extracted text — terminal injection mitigated

## Past audits

See `REDTEAM.md` and `REDTEAM_V2.md` for full adversarial analysis results.
