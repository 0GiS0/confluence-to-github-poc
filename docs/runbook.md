# Runbook: Confluence to Markdown PoC

This runbook reproduces the PoC end to end: seed a Confluence sandbox, export it to Markdown, validate the result, and preview the MkDocs (TechDocs-compatible) site.

## 1. Prerequisites

- Python 3.12 or newer, and `git`.
- Access to a Confluence Cloud site and a classic API token (basic auth).
- Network access to PyPI. If `files.pythonhosted.org` is blocked, or your network requires a package proxy, set `PIP_INDEX_URL` to that proxy before installing (see section 3). Do not install packages globally.

## 2. Credentials

Create `~/.config/confluence-poc/.env` from `.env.example`:

```bash
mkdir -p ~/.config/confluence-poc
cp .env.example ~/.config/confluence-poc/.env
chmod 600 ~/.config/confluence-poc/.env
# edit the file and set CONFLUENCE_URL, CONFLUENCE_USER, CONFLUENCE_API_TOKEN, CONFLUENCE_SPACE_KEY
# optional: CONFLUENCE_ROOT_PAGE_TITLE (defaults to "Engineering Handbook")
```

- `CONFLUENCE_URL` must not include `/wiki`.
- `CONFLUENCE_ROOT_PAGE_TITLE` names the root page whose descendants are exported and validated. It defaults to the seeded `Engineering Handbook`. See section 11 to use your own content.
- Never print, log, or commit the token. Git ignores `.env` and `.env.*`, except `.env.example`.
- Environment variables with the same names override the file, but only when they are non-empty.

## 3. Create the virtual environment

From the repository root (the venv lives inside the worktree):

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

If the default index is unreachable, or your network requires a package proxy, set `PIP_INDEX_URL` to that proxy and install through it:

```bash
PIP_INDEX_URL=https://your-proxy.example.com/pypi/simple/ .venv/bin/python -m pip install -r requirements.txt
```

Pinned versions: `confluence-markdown-exporter==5.6.0` (CLI `cme`), `mkdocs==1.6.1`.

## 4. Seed the Confluence space (idempotent)

> **Warning:** Run the seed only in a dedicated test space. It replaces the content of existing pages whose titles match the synthetic handbook. Name the space "Confluence Migration PoC", because the `nav` in `mkdocs.yml` expects that display name.

```bash
.venv/bin/python scripts/seed_confluence.py
```

Creates or updates 21 pages under the "Engineering Handbook" root, with attachments. Re-running is safe: no duplicate pages are created. Because Confluence normalises stored XHTML, most pages receive a new version on every run even when the content is unchanged.

The seed deliberately uses only built-in macros, plus one unknown macro (`acme-status-widget`) and an `include` macro, to test degradation.

## 5. Export to Markdown

Before the first export on a new site, delete the sample export: the contents of `docs/confluence/`. The repository (and any clone) contains an export from the original site, and its files would otherwise be reported as unreferenced by validation.

```bash
.venv/bin/python scripts/run_export.py
```

- Resolves the root page through the REST API and writes the merged converter config to `.work/cme-config.json` (mode 600, gitignored).
- Runs `cme pages-with-descendants` with `config/cme-settings.json`.
- Output: `docs/confluence/<space name>/...` and `docs/confluence/attachments/`.
- Output: printed to stdout (the `cme` log is not written to a file).

Expected result for the seeded handbook: 21/21 pages, 2/2 attachments, exit 0.

## 6. Validate the export

```bash
.venv/bin/python scripts/validate_export.py
```

Checks that the exported page tree's titles match the Confluence tree, that every relative link matched by the validator's pattern resolves (86 links checked; in-page anchors are reported as warnings), that attachments on disk are referenced by a page, and it lists the macro placeholders. It does not verify hierarchy or compare the attachment inventory against Confluence. Exits 1 on failure.

## 7. Build and preview the MkDocs site

Build with strict mode (fails on warnings):

```bash
.venv/bin/mkdocs build --strict
```

Preview locally on port 8000:

```bash
.venv/bin/mkdocs serve -a 127.0.0.1:8000
```

Open http://127.0.0.1:8000/Confluence%20Migration%20PoC/Engineering%20Handbook/ (the site has no root page). Expect 5 INFO "no such anchor" notes during the build: these are the known degraded TOC links (see `reports/fidelity-matrix.md`, finding D1). They are informational and do not fail the strict build.

## 8. Backstage TechDocs

`catalog-info.yaml` registers the site as a Backstage `Component` with `backstage.io/techdocs-ref: dir:.`. `mkdocs.yml` at the root is the TechDocs entry point.

## 9. Maintenance notes

- `mkdocs.yml` uses an explicit `nav`. Pages that are not listed in `nav` are still built and served, but they do not appear in the sidebar. For your own content, remove the `nav` block so MkDocs generates it.
- The export is a full re-export (`skip_unchanged` is false). `cleanup_stale` removes the output of pages that were moved or deleted since a previous export. It does not remove other files in `docs/confluence/`.
- Remediation items and the fidelity matrix are in `reports/`. They describe the seeded handbook.

## 10. Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `pip` returns HTTP 404 or fails with curl error 35 | Default index or files host blocked | Set `PIP_INDEX_URL` to your package proxy, as shown in section 3 |
| Seed returns HTTP 500 on `include` | Empty `ac:name` parameter | Use `ac:name="page"` (already fixed in `seed_confluence.py`) |
| Export fails on the root page with OSError | Empty ancestor path yields an absolute path | Keep `{space_name}/` at the start of path templates (already set in `config/cme-settings.json`) |
| `Root page '...' not found` | `CONFLUENCE_ROOT_PAGE_TITLE` does not match a page title in the space, or the seed has not run | Check the exact title, or run `seed_confluence.py` for the seeded handbook |
| Validation reports a missing or extra page | Leftover files from another export in `docs/confluence/`, or titles the converter sanitizes into different filenames | Delete the old export and re-run. Pages outside the root tree in Confluence are not counted. Review the output for your content |

## 11. Using your own Confluence content

1. Set `CONFLUENCE_SPACE_KEY` to your space key and `CONFLUENCE_ROOT_PAGE_TITLE` to the exact title of the root page. Titles must be unique in the space.
2. Do not run `seed_confluence.py`.
3. Delete the existing `docs/confluence/` contents (the sample export from the original site) in a disposable clone or branch. Otherwise its leftover files are reported as unreferenced.
4. Run `run_export.py` and then `validate_export.py`.
5. Delete the `nav` block in `mkdocs.yml` (or replace it with your page paths), then run `mkdocs build --strict`.

Notes:

- Exports write to `docs/confluence/`. `cleanup_stale` removes only files the converter previously exported that the new run does not produce.
- `run_export.py` exports a single page tree. Whole-space export is not supported by this wrapper. It would need changes to the root lookup, the converter command, and the validator.
- Links to pages outside the exported tree can become relative links to Markdown files that are not exported. Then validation or the strict build fails. Export those pages too, or repair the links.
- The validator matches Confluence titles to Markdown filenames exactly. Titles with characters the converter sanitizes can be reported as missing. It also reports attachments that no page links to. Review its output rather than treating it as a full audit.
- The reports in `reports/` describe the seeded handbook. Write your own findings from the new export.
