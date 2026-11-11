"""Validate the Markdown export against the live Confluence space.

Checks performed:
  1. Inventory: every page in the space has exactly one exported Markdown file.
  2. Relative links: every local Markdown link and image resolves to an existing file.
  3. Macro artefacts: leftover Confluence storage markup or macro error text.
  4. Attachments: every exported attachment is referenced and exists on disk.

Exit code is 0 when no check fails; warnings are reported but do not fail the run.
"""

import re
import sys
import urllib.parse
from pathlib import Path

from common import ConfluenceClient, ConfluenceError, load_settings

REPO_ROOT = Path(__file__).resolve().parent.parent
EXPORT_ROOT = REPO_ROOT / "docs" / "confluence"
LINK_PATTERN = re.compile(r"!?\[[^\]]*\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
MACRO_ERROR_PATTERN = re.compile(r"Error rendering macro '([^']+)'")
UNKNOWN_MACRO_PATTERN = re.compile(r"unknown-macro\?name=([^&)\s]+)")
STORAGE_MARKUP_PATTERN = re.compile(r"<ac:|<ri:")
ROOT_PAGE_TITLE = "Engineering Handbook"


def fetch_exported_tree_pages(settings: dict) -> dict:
    """Return {title: page_id} for the root page and all of its descendants (the exported tree)."""
    client = ConfluenceClient.from_settings(settings)
    root = client.request("GET", "/content", params={
        "spaceKey": settings["CONFLUENCE_SPACE_KEY"], "title": ROOT_PAGE_TITLE,
    })["results"][0]
    descendants = client.get_all(f"/content/{root['id']}/descendant/page")
    pages = [root, *descendants]
    return {page["title"]: page["id"] for page in pages}


def exported_markdown_files() -> list[Path]:
    return sorted(EXPORT_ROOT.rglob("*.md"))


def check_inventory(space_titles: dict) -> list[str]:
    failures = []
    exported_titles = {path.stem if path.name != "README.md" else path.parent.name for path in exported_markdown_files()}
    for title in sorted(space_titles):
        if title not in exported_titles:
            failures.append(f"page '{title}' is missing from the export")
    if len(exported_markdown_files()) != len(space_titles):
        failures.append(
            f"expected {len(space_titles)} Markdown files, found {len(exported_markdown_files())}"
        )
    return failures


def check_links() -> tuple[list[str], int]:
    failures = []
    checked = 0
    for md_file in exported_markdown_files():
        text = md_file.read_text(encoding="utf-8")
        for target in LINK_PATTERN.findall(text):
            if target.startswith(("http://", "https://", "#", "mailto:")):
                continue
            checked += 1
            path_part = urllib.parse.unquote(target.split("#", 1)[0])
            if not path_part:
                continue
            if not (md_file.parent / path_part).resolve().exists():
                failures.append(f"{md_file.relative_to(REPO_ROOT)} -> {target}")
    return failures, checked


def check_macro_artefacts() -> tuple[dict, list[str], int]:
    """Return counts of degraded macros, unknown macro names, and leftover storage markup."""
    degraded: dict = {}
    unknown_names: set = set()
    leftover = []
    for md_file in exported_markdown_files():
        text = md_file.read_text(encoding="utf-8")
        for macro in MACRO_ERROR_PATTERN.findall(text):
            degraded[macro] = degraded.get(macro, 0) + 1
        unknown_names.update(UNKNOWN_MACRO_PATTERN.findall(text))
        if STORAGE_MARKUP_PATTERN.search(text):
            leftover.append(str(md_file.relative_to(REPO_ROOT)))
    return degraded, sorted(unknown_names), leftover


def check_attachments() -> tuple[list[str], int]:
    attachment_dir = EXPORT_ROOT / "attachments"
    on_disk = sorted(attachment_dir.iterdir()) if attachment_dir.exists() else []
    referenced = set()
    for md_file in exported_markdown_files():
        for target in LINK_PATTERN.findall(md_file.read_text(encoding="utf-8")):
            if "attachments/" in target:
                referenced.add(Path(urllib.parse.unquote(target)).name)
    failures = [f"attachment '{path.name}' is not referenced by any page" for path in on_disk
                if path.name not in referenced]
    return failures, len(on_disk)


def main() -> int:
    settings = load_settings()
    try:
        space_titles = fetch_exported_tree_pages(settings)
    except ConfluenceError as error:
        print(f"Validation aborted: {error}", file=sys.stderr)
        return 1

    failures = []
    failures += check_inventory(space_titles)
    link_failures, links_checked = check_links()
    failures += link_failures
    degraded, unknown_names, leftover = check_macro_artefacts()
    if leftover:
        failures += [f"storage markup left in {path}" for path in leftover]
    attachment_failures, attachment_count = check_attachments()
    failures += attachment_failures

    print(f"Pages in exported tree: {len(space_titles)}; Markdown files: {len(exported_markdown_files())}")
    print(f"Relative links checked: {links_checked}; broken: {len(link_failures)}")
    print(f"Attachments on disk: {attachment_count}")
    print(f"Macro error placeholders: {degraded or 'none'}")
    print(f"Unknown macro placeholders: {unknown_names or 'none'}")
    for failure in failures:
        print(f"FAIL: {failure}")
    print("RESULT:", "FAILED" if failures else "PASSED")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
