# confluence-to-github-poc

Reproducible PoC that migrates technical Confluence content to Markdown in GitHub and reports what needs manual remediation. Tracked in issue [#1](https://github.com/0GiS0/confluence-to-github-poc/issues/1).

## What it does

1. **Seeds** a synthetic handbook (21 pages, attachments, built-in macros, plus one unknown macro and one `include` macro) into a Confluence Cloud Free sandbox. Idempotent.
2. **Exports** it to Markdown with [`confluence-markdown-exporter`](https://spenhouet.github.io/confluence-markdown-exporter/) 5.6.0. Parent pages become `README.md`, attachments are exported, and links are relative.
3. **Validates** the export (page tree, relative links, attachments, macro placeholders).
4. **Builds** a Backstage TechDocs-compatible MkDocs site.

## Repository layout

| Path | Content |
|---|---|
| `docs/confluence/` | Exported Markdown and attachments (browsable on GitHub) |
| `docs/runbook.md` | Step-by-step runbook |
| `reports/fidelity-matrix.md` | Preserved / degraded / lost matrix |
| `reports/remediation-report.md` | Manual remediation items and validation results |
| `scripts/` | `seed_confluence.py`, `run_export.py`, `validate_export.py`, `common.py` |
| `config/cme-settings.json` | Converter settings (no secrets) |
| `mkdocs.yml`, `catalog-info.yaml` | MkDocs site and Backstage registration |

## Quick start

```bash
python3 -m venv .venv && .venv/bin/python -m pip install -r requirements.txt
cp .env.example ~/.config/confluence-poc/.env   # then fill in the values
.venv/bin/python scripts/seed_confluence.py
.venv/bin/python scripts/run_export.py
.venv/bin/python scripts/validate_export.py
.venv/bin/mkdocs build --strict
.venv/bin/mkdocs serve -a 127.0.0.1:8000        # preview at http://127.0.0.1:8000/
```

See [`docs/runbook.md`](docs/runbook.md) for prerequisites, credentials, and troubleshooting.

## Security

Credentials are read from `~/.config/confluence-poc/.env` or environment variables. They are never committed. `.env*` (except `.env.example`), `.venv/`, `.work/`, and `site/` are gitignored.
