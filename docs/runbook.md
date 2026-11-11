# Runbook: Confluence to Markdown PoC

This runbook reproduces the PoC end to end: seed a Confluence sandbox, export it to Markdown, validate the result, and preview the MkDocs (TechDocs-compatible) site.

## 1. Prerequisites

- Python 3.12 or newer, and `git`.
- Access to a Confluence Cloud site and a classic API token (basic auth).
- Network access to a PyPI mirror. If `files.pythonhosted.org` is blocked, set `PIP_INDEX_URL` to your configured package proxy. Do not install packages globally.

## 2. Credentials

Create `~/.config/confluence-poc/.env` from `.env.example`:

```bash
mkdir -p ~/.config/confluence-poc
cp .env.example ~/.config/confluence-poc/.env
chmod 600 ~/.config/confluence-poc/.env
# edit the file and set CONFLUENCE_URL, CONFLUENCE_USER, CONFLUENCE_API_TOKEN, CONFLUENCE_SPACE_KEY
```

- `CONFLUENCE_URL` must not include `/wiki`.
- Never print, log, or commit the token. `.env*` is gitignored.
- Environment variables with the same names override the file.

## 3. Create the virtual environment

From the repository root (the venv lives inside the worktree):

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

If the default index is unreachable, install through the proxy:

```bash
.venv/bin/python -m pip install -i https://packagefeedproxy.microsoft.io/pypi/simple/ -r requirements.txt
```

Pinned versions: `confluence-markdown-exporter==5.6.0` (CLI `cme`), `mkdocs==1.6.1`.

## 4. Seed the Confluence space (idempotent)

```bash
.venv/bin/python scripts/seed_confluence.py
```

Creates or updates 21 pages under the "Engineering Handbook" root, with attachments. Re-running is safe: no duplicate pages are created. Because Confluence normalises stored XHTML, most pages receive a new version on every run even when the content is unchanged.

The seed deliberately uses only built-in macros, plus one unknown macro (`acme-status-widget`) and an `include` macro, to test degradation.

## 5. Export to Markdown

```bash
.venv/bin/python scripts/run_export.py
```

- Resolves the root page through the REST API and writes the merged converter config to `.work/cme-config.json` (mode 600, gitignored).
- Runs `cme pages-with-descendants` with `config/cme-settings.json`.
- Output: `docs/confluence/Confluence Migration PoC/Engineering Handbook/...` and `docs/confluence/attachments/`.
- Log: `.work/export.log`.

Expected result: 21/21 pages, 2/2 attachments, exit 0.

## 6. Validate the export

```bash
.venv/bin/python scripts/validate_export.py
```

Checks that the exported page tree matches Confluence, that every relative link resolves (81 links), that attachments are on disk, and it lists the macro placeholders. Exits 1 on failure.

## 7. Build and preview the MkDocs site

Build with strict mode (fails on warnings):

```bash
.venv/bin/mkdocs build --strict
```

Preview locally on port 8000:

```bash
.venv/bin/mkdocs serve -a 127.0.0.1:8000
```

Open http://127.0.0.1:8000/. Expect 5 INFO "no such anchor" notes during the build: these are the known degraded TOC links (see `reports/fidelity-matrix.md`, finding D1). They are informational and do not fail the strict build.

## 8. Backstage TechDocs

`catalog-info.yaml` registers the site as a Backstage `Component` with `backstage.io/techdocs-ref: dir:.`. `mkdocs.yml` at the root is the TechDocs entry point.

## 9. Maintenance notes

- `mkdocs.yml` uses an explicit `nav`. A page added to the export does not appear in the site until it is added to `nav`.
- The export is a full re-export (`skip_unchanged` is false). Stale files are removed (`cleanup_stale` is true).
- Remediation items and the fidelity matrix are in `reports/`.

## 10. Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `pip` returns HTTP 404 or fails with curl error 35 | Default index or files host blocked | Use the proxy index shown in section 3 |
| Seed returns HTTP 500 on `include` | Empty `ac:name` parameter | Use `ac:name="page"` (already fixed in `seed_confluence.py`) |
| Export fails on the root page with OSError | Empty ancestor path yields an absolute path | Keep `{space_name}/` at the start of path templates (already set in `config/cme-settings.json`) |
| Validation reports a missing or extra page | Space has pages outside the handbook tree | Validation is scoped to the root page's descendants; re-run after the seed |
