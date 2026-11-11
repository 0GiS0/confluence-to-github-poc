"""Export the seeded Confluence page tree to Markdown with confluence-markdown-exporter (cme).

The committed settings live in config/cme-settings.json. At runtime this script merges
the credentials from ~/.config/confluence-poc/.env into a private, gitignored config
file under .work/ (mode 600) and points cme at it through CME_CONFIG_PATH.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

from common import ConfluenceClient, ConfluenceError, load_settings

REPO_ROOT = Path(__file__).resolve().parent.parent
SETTINGS_FILE = REPO_ROOT / "config" / "cme-settings.json"
WORK_DIR = REPO_ROOT / ".work"
CME_CONFIG = WORK_DIR / "cme-config.json"
ROOT_PAGE_TITLE = "Engineering Handbook"


def find_root_page_id(client: ConfluenceClient, space_key: str) -> str:
    """Return the id of the root page of the seeded tree."""
    result = client.request("GET", "/content", params={
        "spaceKey": space_key, "title": ROOT_PAGE_TITLE, "expand": "space",
    })
    results = result.get("results", [])
    if not results:
        raise SystemExit(f"Root page '{ROOT_PAGE_TITLE}' not found in space {space_key}. Run seed_confluence.py first.")
    return results[0]["id"]


def write_private_config(settings: dict) -> None:
    """Write the cme config with the credentials, readable only by the current user."""
    config = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
    config["auth"] = {
        "confluence": {
            settings["CONFLUENCE_URL"]: {
                "username": settings["CONFLUENCE_USER"],
                "api_token": settings["CONFLUENCE_API_TOKEN"],
            }
        },
        "jira": {},
    }
    WORK_DIR.mkdir(exist_ok=True)
    fd = os.open(CME_CONFIG, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        json.dump(config, handle, indent=2)


def main() -> int:
    settings = load_settings()
    client = ConfluenceClient.from_settings(settings)
    try:
        page_id = find_root_page_id(client, settings["CONFLUENCE_SPACE_KEY"])
    except ConfluenceError as error:
        print(f"Export failed: {error}", file=sys.stderr)
        return 1

    write_private_config(settings)
    page_url = f"{settings['CONFLUENCE_URL']}/wiki/spaces/{settings['CONFLUENCE_SPACE_KEY']}/pages/{page_id}"
    env = {**os.environ, "CME_CONFIG_PATH": str(CME_CONFIG)}
    cme = Path(sys.executable).parent / "cme"
    command = [str(cme), "pages-with-descendants", page_url]
    print(f"Running cme against root page id {page_id} (config: .work/cme-config.json)")
    completed = subprocess.run(command, cwd=REPO_ROOT, env=env, check=False)
    return completed.returncode


if __name__ == "__main__":
    sys.exit(main())
