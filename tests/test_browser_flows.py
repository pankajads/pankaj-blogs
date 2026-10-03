"""Drive the real Playwright flow against stand-in pages served via request interception.

These prove the control flow (fill, click, wait, error handling). They cannot prove that the
selectors match the live Medium UI; only a --dry-run on the author's machine does that.
"""

from datetime import date
from pathlib import Path

import pytest

pw = pytest.importorskip("playwright.sync_api")

from publisher import medium  # noqa: E402
from publisher.post import Post  # noqa: E402

REDIRECT = "<script>location.replace('{to}')</script>"
MEDIUM_IMPORT = """<html><body><input type="url" placeholder="https://yoursite.com/story">
<button onclick="location.href='https://medium.com/p/import/done'">Import</button></body></html>"""
MEDIUM_DONE = """<html><body><a href="https://medium.com/p/abc123/edit">See your story</a></body></html>"""
MEDIUM_EDITOR = "<html><body>editor</body></html>"


@pytest.fixture
def page():
    with pw.sync_playwright() as p:
        browser = p.chromium.launch()
        pg = browser.new_page()
        yield pg
        browser.close()


def serve(page, routes: dict[str, str]):
    def handler(route):
        url = route.request.url
        for prefix, html in routes.items():
            if url.startswith(prefix):
                return route.fulfill(status=200, content_type="text/html", body=html)
        return route.fulfill(status=404, body="not found")

    page.route("https://**/*", handler)


POST = Post(
    path=Path("2026-10-05-late-feedback.md"),
    title="Late feedback",
    date=date(2026, 10, 5),
    slug="late-feedback",
    tags=["leadership"],
    canonical_url="https://pankajads.github.io/pankaj-blogs/2026/10/late-feedback/",
)


def test_medium_import_creates_draft_and_stops(page):
    serve(
        page,
        {
            "https://medium.com/p/import/done": MEDIUM_DONE,
            "https://medium.com/p/import": MEDIUM_IMPORT,
            "https://medium.com/p/abc123/edit": MEDIUM_EDITOR,
        },
    )
    assert medium.import_draft(page, POST, dry_run=False) == "https://medium.com/p/abc123/edit"


def test_medium_dry_run_stops_before_import(page):
    serve(page, {"https://medium.com/p/import": MEDIUM_IMPORT})
    assert medium.import_draft(page, POST, dry_run=True) is None
    assert page.input_value('input[type="url"]') == POST.canonical_url
    assert page.url.endswith("/p/import")


def test_medium_signin_redirect_raises(page):
    serve(
        page,
        {
            "https://medium.com/p/import": REDIRECT.format(to="https://medium.com/m/signin"),
            "https://medium.com/m/signin": "<html>sign in</html>",
        },
    )
    with pytest.raises(medium.NotLoggedIn):
        medium.import_draft(page, POST, dry_run=True, timeout_ms=4000)
