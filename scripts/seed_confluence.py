"""Idempotently seed the Confluence POC space with synthetic technical content.

The content deliberately uses only built-in macros (info, code, toc, children,
include, details, anchor, expand, status, tasks, links, images, attachments)
plus one unknown macro (acme-status-widget) to test graceful degradation.

Re-running the script updates pages whose body changed, keeps existing
attachments (replacing their data) and never creates duplicate titles.
"""

import struct
import sys
import zlib
from xml.sax.saxutils import escape

from common import ConfluenceClient, ConfluenceError, load_settings

ROOT = "Engineering Handbook"


def link(title: str, text: str) -> str:
    """Internal page link in storage format."""
    return (
        f'<ac:link><ri:page ri:content-title="{escape(title)}"/>'
        f"<ac:plain-text-link-body><![CDATA[{text}]]></ac:plain-text-link-body></ac:link>"
    )


def info(text: str) -> str:
    return (
        '<ac:structured-macro ac:name="info"><ac:rich-text-body>'
        f"<p>{text}</p></ac:rich-text-body></ac:structured-macro>"
    )


def warning(text: str) -> str:
    return (
        '<ac:structured-macro ac:name="warning"><ac:rich-text-body>'
        f"<p>{text}</p></ac:rich-text-body></ac:structured-macro>"
    )


def code(language: str, source: str) -> str:
    return (
        '<ac:structured-macro ac:name="code">'
        f'<ac:parameter ac:name="language">{language}</ac:parameter>'
        f"<ac:plain-text-body><![CDATA[{source}]]></ac:plain-text-body></ac:structured-macro>"
    )


def status(colour: str, title: str) -> str:
    return (
        '<ac:structured-macro ac:name="status">'
        f'<ac:parameter ac:name="colour">{colour}</ac:parameter>'
        f'<ac:parameter ac:name="title">{title}</ac:parameter></ac:structured-macro>'
    )


def tasks(*items: tuple[bool, str]) -> str:
    rows = "".join(
        f"<ac:task><ac:task-id>{i}</ac:task-id>"
        f"<ac:task-status>{'complete' if done else 'incomplete'}</ac:task-status>"
        f"<ac:task-body>{text}</ac:task-body></ac:task>"
        for i, (done, text) in enumerate(items, start=1)
    )
    return f"<ac:task-list>{rows}</ac:task-list>"


UNKNOWN_MACRO = (
    '<ac:structured-macro ac:name="acme-status-widget">'
    '<ac:parameter ac:name="service">payments</ac:parameter></ac:structured-macro>'
)

TABLE_SERVICES = (
    "<table><tbody>"
    "<tr><th>Service</th><th>Owner</th><th>Tier</th></tr>"
    "<tr><td>payments-api</td><td>Team Payments</td><td>1</td></tr>"
    "<tr><td>catalog-api</td><td>Team Catalog</td><td>2</td></tr>"
    "<tr><td>batch-reports</td><td>Team Data</td><td>3</td></tr>"
    "</tbody></table>"
)

# Each page: title, parent title (None for the root), labels, storage-format body.
PAGES = [
    {"title": ROOT, "parent": None, "labels": ["poc", "handbook"], "body": (
        info("Synthetic handbook used by the Confluence to Markdown PoC. All content is fictional.")
        + '<ac:structured-macro ac:name="toc"/>'
        + "<h2>Sections</h2>"
        + '<ac:structured-macro ac:name="children"><ac:parameter ac:name="all">true</ac:parameter></ac:structured-macro>'
    )},
    {"title": "Platform Operations", "parent": ROOT, "labels": ["operations"], "body": (
        "<p>How the platform is deployed, observed and recovered.</p>"
        + '<ac:structured-macro ac:name="children"/>'
    )},
    {"title": "Deployment Guide", "parent": "Platform Operations", "labels": ["operations", "deployment"], "body": (
        '<ac:structured-macro ac:name="toc"/>'
        + "<h2>Prerequisites</h2>"
        + tasks((True, "Access to the Kubernetes cluster"), (True, "Release tag approved"), (False, "Change ticket created"))
        + "<h2>Deploy</h2>"
        + "<p>Run the pipeline and follow the steps below. See "
        + link("Rollback Procedure", "rollback procedure")
        + " if the rollout fails.</p>"
        + code("bash", "kubectl -n payments rollout status deploy/payments-api --timeout=5m")
        + '<h2 id="status">Current status</h2>'
        + status("Green", "Production stable")
        + " "
        + status("Yellow", "Staging degraded")
        + '<ac:structured-macro ac:name="anchor"><ac:parameter ac:name="">post-deploy</ac:parameter></ac:structured-macro>'
        + "<h2>Post-deploy checks</h2><p>Check the dashboards before closing the change.</p>"
    )},
    {"title": "Rollback Procedure", "parent": "Deployment Guide", "labels": ["operations", "deployment"], "body": (
        warning("Rollback is only safe for backward compatible migrations.")
        + "<ol><li>Freeze the pipeline.</li><li>Redeploy the previous image tag.</li><li>Verify health endpoints.</li></ol>"
        + code("bash", "kubectl -n payments rollout undo deploy/payments-api")
    )},
    {"title": "Incident Response", "parent": "Platform Operations", "labels": ["operations", "incident"], "body": (
        "<p>Incidents are classified by severity and followed by a postmortem.</p>"
        + '<ac:structured-macro ac:name="expand"><ac:parameter ac:name="title">On-call contacts</ac:parameter>'
        + "<ac:rich-text-body><p>Primary and secondary rotations live in the on-call tool.</p></ac:rich-text-body></ac:structured-macro>"
        + '<ac:structured-macro ac:name="children"/>'
    )},
    {"title": "Severity Levels", "parent": "Incident Response", "labels": ["incident"], "body": (
        "<table><tbody><tr><th>Level</th><th>Description</th><th>Response</th></tr>"
        "<tr><td>SEV1</td><td>Full outage</td><td>Page immediately</td></tr>"
        "<tr><td>SEV2</td><td>Partial degradation</td><td>Page during business hours</td></tr>"
        "<tr><td>SEV3</td><td>Minor defect</td><td>Ticket</td></tr></tbody></table>"
    )},
    {"title": "Postmortem Template", "parent": "Incident Response", "labels": ["incident", "template"], "body": (
        "<h2>Summary</h2><p>What happened, for how long, and who was affected.</p>"
        + "<h2>Timeline</h2>"
        + tasks((True, "Detection"), (True, "Mitigation"), (False, "Root cause confirmed"))
        + "<h2>Action items</h2><p>Each action item needs an owner and a due date.</p>"
    )},
    {"title": "Network Topology", "parent": "Platform Operations", "labels": ["operations", "network"], "body": (
        "<p>Current topology of the payments and catalog services.</p>"
        + '<p><ac:image ac:width="640"><ri:attachment ri:filename="network-topology.png"/></ac:image></p>'
        + '<p>Full diagram export: <ac:link><ri:attachment ri:filename="network-topology.pdf"/>'
        + "<ac:plain-text-link-body><![CDATA[PDF diagram]]></ac:plain-text-link-body></ac:link></p>"
        + "<h2>Services</h2>" + TABLE_SERVICES
    )},
    {"title": "Metrics and Observability", "parent": "Platform Operations", "labels": ["observability"], "body": (
        "<p>The key metrics are p95 latency, error rate, and saturation.</p>"
        + '<ac:structured-macro ac:name="details"><ac:rich-text-body>'
        + "<table><tbody><tr><th>Owner</th><td>Team Observability</td></tr>"
        + "<tr><th>Review cadence</th><td>Monthly</td></tr></tbody></table></ac:rich-text-body></ac:structured-macro>"
        + "<h2>Dashboards</h2><p>Dashboards are linked from the service catalog.</p>"
        + '<p>Status widget: ' + UNKNOWN_MACRO + "</p>"
    )},
    {"title": "Development Practices", "parent": ROOT, "labels": ["development"], "body": (
        "<p>Conventions shared by all engineering teams.</p>"
        + '<ac:structured-macro ac:name="children"/>'
    )},
    {"title": "Coding Standards", "parent": "Development Practices", "labels": ["development", "standards"], "body": (
        "<p>Follow the language specific guides and keep functions small.</p>"
        + '<ac:structured-macro ac:name="children"/>'
    )},
    {"title": "Python Style", "parent": "Coding Standards", "labels": ["development", "python"], "body": (
        "<p>Use type hints and format with <code>ruff format</code>.</p>"
        + code("python", "def add(a: int, b: int) -> int:\n    return a + b")
        + info("Prefer dataclasses for simple value objects.")
    )},
    {"title": "Git Workflow", "parent": "Coding Standards", "labels": ["development", "git"], "body": (
        "<p>Use short-lived branches and Conventional Commits.</p>"
        + code("bash", "git switch -c feat/123-add-search\ngit commit -m 'feat: add search endpoint'")
        + tasks((True, "Branch from main"), (False, "Open a pull request after review"))
    )},
    {"title": "Code Review Checklist", "parent": "Development Practices", "labels": ["development", "review"], "body": (
        tasks((True, "Tests cover the change"), (True, "No secrets in the diff"), (False, "Docs updated"))
        + "<p>See " + link("Coding Standards", "coding standards") + " for details.</p>"
    )},
    {"title": "Security & Compliance", "parent": ROOT, "labels": ["security"], "body": (
        "<p>Security controls required for every production service.</p>"
        + '<ac:structured-macro ac:name="children"/>'
    )},
    {"title": "Access Control Policy", "parent": "Security & Compliance", "labels": ["security", "policy"], "body": (
        "<p>Least privilege applies. Access is granted through groups, reviewed quarterly.</p>"
        + warning("Shared accounts are not allowed in production.")
    )},
    {"title": "Secrets Management", "parent": "Security & Compliance", "labels": ["security"], "body": (
        "<p>Secrets live in the vault. Never commit them to repositories.</p>"
        + code("bash", "vault kv get secret/payments/api-key")
        + '<p>Reference: <ac:link><ri:page ri:content-title="Access Control Policy"/></ac:link></p>'
    )},
    {"title": "Onboarding", "parent": ROOT, "labels": ["onboarding"], "body": (
        "<p>Everything a new engineer needs during the first weeks.</p>"
        + '<ac:structured-macro ac:name="children"/>'
    )},
    {"title": "Dev Environment Setup", "parent": "Onboarding", "labels": ["onboarding", "setup"], "body": (
        "<p>Install the toolchain: Python 3.12, Node 22 and Docker Desktop.</p>"
        + code("bash", "python3 -m venv .venv && .venv/bin/pip install -r requirements.txt")
        + info("Use the company VPN when pulling internal packages.")
    )},
    {"title": "First Week Checklist", "parent": "Onboarding", "labels": ["onboarding"], "body": (
        tasks((False, "Get repository access"), (False, "Complete security training"), (False, "Pair on a starter ticket"))
        + "<h2>Environment</h2>"
        + '<ac:structured-macro ac:name="include"><ac:parameter ac:name="page"><ri:page ri:content-title="Dev Environment Setup"/></ac:parameter></ac:structured-macro>'
    )},
    {"title": "Team Glossary", "parent": "Onboarding", "labels": ["onboarding", "glossary"], "body": (
        "<table><tbody><tr><th>Term</th><th>Meaning</th></tr>"
        "<tr><td>SLO</td><td>Service level objective</td></tr>"
        "<tr><td>Toil</td><td>Manual, repetitive operational work</td></tr>"
        "<tr><td>Canary</td><td>Partial rollout to a small share of traffic</td></tr></tbody></table>"
    )},
]


def make_png(width: int = 320, height: int = 180) -> bytes:
    """Build a small valid PNG with a gradient, using only the standard library."""
    # Each scanline starts with filter byte 0 (no filter), followed by RGB pixels.
    rows = b"".join(
        b"\x00" + bytes(channel for x in range(width) for channel in (x * 255 // width, y * 255 // height, 128))
        for y in range(height)
    )

    def chunk(kind: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)

    header = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", header) + chunk(b"IDAT", zlib.compress(rows)) + chunk(b"IEND", b"")


def make_pdf() -> bytes:
    """Build a minimal one-page PDF with correct cross-reference offsets."""
    stream = b"BT /F1 18 Tf 40 120 Td (Network topology - synthetic PoC) Tj ET"
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 400 200] /Contents 4 0 R "
        b"/Resources << /Font << /F1 5 0 R >> >> >>",
        b"<< /Length %d >>\nstream\n" % len(stream) + stream + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    out = bytearray(b"%PDF-1.4\n")
    offsets = []
    for number, body in enumerate(objects, start=1):
        offsets.append(len(out))
        out += b"%d 0 obj\n" % number + body + b"\nendobj\n"
    xref_at = len(out)
    out += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objects) + 1)
    for offset in offsets:
        out += b"%010d 00000 n \n" % offset
    out += b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (len(objects) + 1, xref_at)
    return bytes(out)


ATTACHMENTS = {
    "Network Topology": [
        ("network-topology.png", make_png, "image/png"),
        ("network-topology.pdf", make_pdf, "application/pdf"),
    ],
}


def find_page(client: ConfluenceClient, space_key: str, title: str) -> dict | None:
    result = client.request("GET", "/content", params={
        "spaceKey": space_key, "title": title, "expand": "version,ancestors,body.storage",
    })
    results = result.get("results", []) if result else []
    return results[0] if results else None


def ensure_page(client, space_key, spec, page_ids):
    """Create the page or update it when the stored body differs. Returns the page id."""
    parent_id = page_ids.get(spec["parent"]) if spec["parent"] else None
    ancestors = [{"id": int(parent_id)}] if parent_id else []
    existing = find_page(client, space_key, spec["title"])
    if existing is None:
        created = client.request("POST", "/content", payload={
            "type": "page", "title": spec["title"], "space": {"key": space_key},
            "ancestors": ancestors,
            "body": {"storage": {"value": spec["body"], "representation": "storage"}},
        })
        print(f"created  {spec['title']}")
        return created["id"]
    current_body = existing["body"]["storage"]["value"]
    current_parent = existing.get("ancestors", [])
    current_parent_id = str(current_parent[-1]["id"]) if current_parent else None
    if current_body == spec["body"] and current_parent_id == (str(parent_id) if parent_id else None):
        print(f"unchanged {spec['title']}")
        return existing["id"]
    client.request("PUT", f"/content/{existing['id']}", payload={
        "id": existing["id"], "type": "page", "title": spec["title"],
        "version": {"number": existing["version"]["number"] + 1},
        "ancestors": ancestors,
        "body": {"storage": {"value": spec["body"], "representation": "storage"}},
    })
    print(f"updated  {spec['title']}")
    return existing["id"]


def ensure_labels(client, page_id, labels):
    client.request("POST", f"/content/{page_id}/label",
                   payload=[{"prefix": "global", "name": name} for name in labels])


def ensure_attachments(client, page_id, title):
    for filename, factory, mime_type in ATTACHMENTS.get(title, []):
        existing = client.request("GET", f"/content/{page_id}/child/attachment", params={"filename": filename})
        existing_id = existing["results"][0]["id"] if existing and existing.get("results") else None
        client.upload_attachment(page_id, filename, factory(), mime_type, existing_id=existing_id)
        print(f"attached {title}: {filename} ({'replaced' if existing_id else 'new'})")


def main() -> int:
    settings = load_settings()
    space_key = settings["CONFLUENCE_SPACE_KEY"]
    client = ConfluenceClient.from_settings(settings)
    client.request("GET", f"/space/{space_key}")  # fails fast on bad credentials or space key
    page_ids: dict[str, str] = {}
    for spec in PAGES:
        page_id = str(ensure_page(client, space_key, spec, page_ids))
        page_ids[spec["title"]] = page_id
        ensure_labels(client, page_id, spec["labels"])
        ensure_attachments(client, page_id, spec["title"])
    print(f"seeded {len(page_ids)} pages in space {space_key}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except ConfluenceError as exc:
        print(f"Seed failed: {exc}", file=sys.stderr)
        sys.exit(1)
