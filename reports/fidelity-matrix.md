# Fidelity matrix: Confluence storage format to Markdown

Converter: `confluence-markdown-exporter` 5.6.0 (`cme`), settings in `config/cme-settings.json`.
Source: 21 pages under "Engineering Handbook" in space `POC` (Confluence Cloud Free), seeded by `scripts/seed_confluence.py`.

Status legend:
- **Preserved**: the content and structure survive as readable Markdown or inline HTML with no manual work.
- **Degraded**: the content survives, but the behaviour or links do not match the source. Manual fix is recommended.
- **Lost**: the content is replaced by an error or placeholder. Manual rewrite is required.

## Matrix

| # | Element (Confluence source) | Page | Exported as | Status | Notes |
|---|---|---|---|---|---|
| 1 | Page hierarchy (parent/child) | All | Folders with `README.md` for parents, `<Title>.md` for leaves | Preserved | Parents become `README.md` (index) so MkDocs and GitHub both render them. |
| 2 | Headings (h1-h4) | All | `#` to `####` | Preserved | |
| 3 | Paragraphs, bold, italic, inline code | All | Markdown equivalents | Preserved | |
| 4 | Bulleted and numbered lists | All | Markdown lists | Preserved | |
| 5 | Task lists (checkboxes) | First Week Checklist, others | GFM `- [ ]` / `- [x]` | Preserved | |
| 6 | Tables (with header row) | Network Topology, Severity Levels, Team Glossary | Pipe tables | Preserved | |
| 7 | Code block (`code` macro, language set) | Deployment Guide, Rollback Procedure, Secrets Management | Fenced block with language | Preserved | |
| 8 | Info / Warning / Note panels (`info`, `warning`, `note`) | Several | `> [!IMPORTANT]` / `> [!CAUTION]` callouts | Preserved | Renders as an admonition in MkDocs; GitHub renders it as an alert. |
| 9 | Expand macro (`expand`, "On-call contacts") | Incident Response | `<details>` / `<summary>` | Preserved | Raw HTML; renders in both GitHub and MkDocs. |
| 10 | Status lozenge (`status`, coloured) | Several | `<mark style="background: ...">` text | Preserved | Colour kept as inline style; not a semantic badge. |
| 11 | Details / page properties (`details`) | Metrics and Observability | YAML frontmatter plus a table | Preserved | |
| 12 | Attachments (PNG image, PDF) | Network Topology | `docs/confluence/attachments/<id>.<ext>`, referenced relatively | Preserved | Both files exported. Filenames are IDs, so the original names are lost. |
| 13 | Internal page links (`ri:page`) | Breadcrumbs, cross-page links | Relative `.md` links | Preserved | 86 links checked (relative and in-page anchors), 0 broken files; 5 unresolved in-page anchors reported as warnings (`scripts/validate_export.py`). |
| 14 | Breadcrumb / navigation link to parent | Child pages | `../README.md`-style links | Preserved | |
| 15 | Table of contents macro (`toc`, `children`) | Engineering Handbook, Deployment Guide | Static list of Confluence-style `#<page>-<heading>` anchors | Degraded | The anchors do not exist in MkDocs output. See finding D1. |
| 16 | Anchor macro (`anchor`, "post-deploy") | Deployment Guide | Removed (no output) | Degraded | The named anchor is not carried over, so the link to `#post-deploy` has no target. Replace with an explicit heading id if needed. |
| 17 | `include` macro (embedded page) | First Week Checklist | Literal text: "Error rendering macro 'include' : ... No title provided." | Lost | The included content is absent. See finding L1. |
| 18 | Unknown / unsupported macro (`acme-status-widget`) | Metrics and Observability | External placeholder image URL | Lost | No content is kept. See finding L2. |
| 19 | Page comments | None seeded | Not exported (`comments_export` = `none`) | Lost (by design) | Out of scope for this PoC. |
| 20 | Marketplace macros (draw.io, Gliffy) | Not seeded | n/a | Not tested | Free plan has no Marketplace apps. |
| 21 | Page restrictions / permissions | n/a | n/a | Not applicable | Out of scope. |

## Findings

- **L1 (Lost) `include` macro**: the export emits an error string instead of the included content. Manual step: copy the included page into the page that embeds it, or export the source page and reference it with a link.
- **L2 (Lost) unknown macro**: the converter has no handler for `acme-status-widget`, so it outputs an external placeholder image. Manual step: replace the image with the real status content, or add a custom handler to the converter.
- **D1 (Degraded) TOC anchors**: five links use Confluence heading anchors (`#engineeringhandbook-sections`, `#deploymentguide-prerequisites`, `#deploymentguide-deploy`, `#deploymentguide-currentstatus`, `#deploymentguide-post-deploychecks`). MkDocs generates different ids, so these links are broken (5 INFO "no such anchor" notes in `mkdocs build --strict`). Manual step: rewrite the links to MkDocs heading ids, or remove the static TOC and rely on the MkDocs sidebar.
- **D2 (Degraded) anchor macro**: the `post-deploy` anchor disappears, so any link to it is dead. Manual step: add an explicit `{ #post-deploy }` attribute or a heading with that id.
- **Attachment names**: attachments are renamed to their Confluence ids. Manual step (optional): rename them and update the links.
