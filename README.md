# confluence-to-github-poc

A reproducible proof of concept that migrates technical Confluence Cloud content to Markdown in GitHub and reports what needs manual remediation. The result is a browsable Markdown tree in the repository, plus a MkDocs site that Backstage TechDocs can publish.

## What the PoC does

1. **Seeds** a synthetic "Engineering Handbook" into a Confluence Cloud space: 21 pages, attachments, built-in macros, one unknown macro and one `include` macro to test degradation. The seed is idempotent.
2. **Exports** the page tree to Markdown with [`confluence-markdown-exporter`](https://spenhouet.com/confluence-markdown-exporter/) 5.6.0 (`cme`). Parent pages become `README.md`, attachments are downloaded, and links are relative.
3. **Validates** the export: page inventory, relative links, attachments, and leftover macro placeholders.
4. **Builds** a TechDocs-compatible MkDocs site from the exported Markdown.

The PoC is designed to be read and rerun. Nothing is migrated by hand.

## Prerequisites

- **Confluence Cloud site.** The free tier works. You need a space where you can create pages.
- **Classic Atlassian API token.** Create one by following [Manage API tokens for your Atlassian account](https://support.atlassian.com/atlassian-account/docs/manage-api-tokens-for-your-atlassian-account/).
- **Python 3.12 or newer** and **git**.
- Network access to PyPI, or to your organization's package proxy (see [Package proxy](#package-proxy)).

## Configuration

Copy the template to a private file outside the repository and fill in your values:

```bash
mkdir -p ~/.config/confluence-poc
cp .env.example ~/.config/confluence-poc/.env
chmod 600 ~/.config/confluence-poc/.env
```

The scripts read `~/.config/confluence-poc/.env`. Only non-empty environment variables with the same names override the file. Never commit real values. Git ignores `.env` and `.env.*`; `.env.example` is the only tracked file that matches that pattern.

| Variable | Required | Description |
|---|---|---|
| `CONFLUENCE_URL` | Yes | Base URL of your site, for example `https://your-site.atlassian.net`. Do not add `/wiki`. |
| `CONFLUENCE_USER` | Yes | The Atlassian account email used to create the API token. |
| `CONFLUENCE_API_TOKEN` | Yes | The classic API token from the prerequisites. Treat it as a password. |
| `CONFLUENCE_SPACE_KEY` | Yes | Key of the space to seed or export, for example `POC`. |
| `CONFLUENCE_ROOT_PAGE_TITLE` | No | Title of the root page whose page tree is exported. Defaults to `Engineering Handbook`, the seeded tree. Set it to export your own content. |

## Quick start

Run these commands from the repository root in a POSIX shell (Linux, macOS, or WSL on Windows).

- **Seed only a dedicated test space.** `seed_confluence.py` creates pages and replaces the content of pages with the same titles. Do not run it in a space that holds real content.
- **Name the space "Confluence Migration PoC".** The export writes under the space's display name, and the `nav` in `mkdocs.yml` expects that name. Use a different name only after you remove `nav` (see below).

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python scripts/seed_confluence.py      # 1. create the synthetic handbook in Confluence
.venv/bin/python scripts/run_export.py           # 2. export it to docs/confluence/
.venv/bin/python scripts/validate_export.py      # 3. check the export against Confluence
.venv/bin/mkdocs build --strict                  # 4. build the MkDocs site into site/
.venv/bin/mkdocs serve -a 127.0.0.1:8000         # 5. preview the site
```

- **Clear the sample export first on a new site.** The repository contains an export from the original site. Before step 2, delete the contents of `docs/confluence/` (or work in a fresh clone). Otherwise its files remain and validation reports them as unreferenced.
- **Preview URL.** Open http://127.0.0.1:8000/Confluence%20Migration%20PoC/Engineering%20Handbook/. The site has no root page, so use this path or the **Home** entry in the sidebar.

Step 3 needs Confluence access. Steps 4 and 5 work offline.

### Package proxy

If your network blocks the default PyPI index, point pip at your package proxy by setting `PIP_INDEX_URL` before installing:

```bash
PIP_INDEX_URL=https://your-proxy.example.com/pypi/simple/ .venv/bin/python -m pip install -r requirements.txt
```

## Use your own Confluence content

The scripts export one page tree: a root page and all of its descendants. To use your own space instead of the seeded handbook:

1. **Set the variables.** Set `CONFLUENCE_SPACE_KEY` to your space key and `CONFLUENCE_ROOT_PAGE_TITLE` to the exact title of the root page. Page titles must be unique within the space.
2. **Skip the seed.** Do not run `seed_confluence.py`. It creates the synthetic handbook.
3. **Clear the sample export.** The repository includes an export of the seeded handbook from the original site. Run the new export in a disposable clone or a branch, and delete the existing `docs/confluence/` contents first. Otherwise the leftover files remain and validation reports them as unreferenced.
4. **Export and validate.** Run `run_export.py` and then `validate_export.py`.
5. **Update the site navigation.** `mkdocs.yml` has an explicit `nav:` that lists the synthetic pages. Delete the `nav:` block so MkDocs generates navigation from the files, or replace it with your own page paths. Then run `mkdocs build --strict`.

Things to know before you run it:

- Exports write to `docs/confluence/`. `cleanup_stale` removes only files the converter previously exported that the new run does not produce. Files that are not converter output, such as the sample export from another site, are not removed. That is why the sample export must be deleted first.
- **Only a page tree is exported.** `run_export.py` runs `cme pages-with-descendants` on one root page. Whole-space export is not supported by this wrapper. Adding it would need changes to the root lookup, the converter command, and the validator.
- **Links outside the tree may break.** Links to pages outside the exported tree can become relative links to Markdown files that are not exported, and then validation or the strict build fails. Either export those pages too, or repair the links by hand.
- **The validator is written for the sample.** It matches Confluence titles to Markdown filenames exactly, so titles with characters that the converter sanitizes (for example `:`) can be reported as missing. It also reports attachments that no page links to. Review its output, do not treat it as a full migration audit.
- **The reports describe the sample.** `reports/fidelity-matrix.md` and `reports/remediation-report.md` describe the seeded handbook. Neither script regenerates them. Write your own findings from the new export.

## Outputs

| Path | Content |
|---|---|
| `docs/confluence/<Space name>/...` | Exported Markdown. Parent pages become `README.md`, and each page keeps its hierarchy. |
| `docs/confluence/attachments/` | Downloaded attachments, referenced by relative links. |
| `reports/fidelity-matrix.md` | Matrix of the sampled Confluence elements, each with a status: **Preserved**, **Degraded**, **Lost**, or not tested or not applicable. |
| `reports/remediation-report.md` | Validation results and the items that need manual work. |
| `site/` | Built MkDocs site (generated, gitignored). |

### Reading the reports

- **`reports/fidelity-matrix.md`** answers "what survives the migration?". Each row is a Confluence element, such as headings, tables, macros, or links. **Preserved** means it is readable with no work. **Degraded** means the content is there, but a behavior or link does not match the source, so a fix is recommended. **Lost** means the content is replaced by a placeholder or omitted by design, so a manual rewrite may be needed.
- **`reports/remediation-report.md`** answers "what do I need to fix?". It lists the validation results, then the manual items with the pages and reasons, and notes on the export process.

## Backstage TechDocs

The exported tree is also a Backstage TechDocs site:

- `mkdocs.yml` at the repository root is the TechDocs entry point. `docs_dir` points at `docs/confluence/`.
- `catalog-info.yaml` registers the site as a Backstage `Component` with the annotation `backstage.io/techdocs-ref: dir:.`.

For an end-to-end example of a Backstage instance that renders docs like this one, see [0GiS0/backstage-copilot-docs-poc](https://github.com/0GiS0/backstage-copilot-docs-poc).

## Repository layout

| Path | Content |
|---|---|
| `docs/confluence/` | Exported Markdown and attachments, browsable on GitHub |
| `docs/runbook.md` | Detailed step-by-step reference, with troubleshooting |
| `reports/` | Fidelity matrix and remediation report |
| `scripts/` | `seed_confluence.py`, `run_export.py`, `validate_export.py`, `common.py` |
| `config/cme-settings.json` | Converter settings (no secrets) |
| `mkdocs.yml`, `catalog-info.yaml` | MkDocs site and Backstage registration |
| `.env.example` | Configuration template |

## Security

Credentials are read from `~/.config/confluence-poc/.env` or environment variables and are never committed. The export writes a private, gitignored `.work/cme-config.json` with mode 600. Git ignores `.env` and `.env.*` (except `.env.example`), `.venv/`, `.work/`, and `site/`.

See [`docs/runbook.md`](docs/runbook.md) for the detailed runbook and troubleshooting.
