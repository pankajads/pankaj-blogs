"""Drive the real Playwright flows against stand-in pages served via request interception.

These prove the control flow (fill, click, wait, error handling). They cannot prove that the
selectors match the live Medium/Reddit UI; only a --dry-run on the author's machine does that.
"""

from datetime import date
from pathlib import Path

import pytest

pw = pytest.importorskip("playwright.sync_api")

from publisher import medium, reddit  # noqa: E402
from publisher.post import Post, RedditSubmission  # noqa: E402

REDDIT_FORM = """<html><body><form id="newlink">
<textarea name="title"></textarea><textarea name="text"></textarea>
<span class="error" style="display:none">you are doing that too much</span>
<button type="button" name="submit" onclick="{action}">submit</button></form></body></html>"""

REDIRECT = "<script>location.replace('{to}')</script>"
MEDIUM_IMPORT = """<html><body><input type="url" placeholder="https://yoursite.com/story">
<button onclick="location.href='https://medium.com/p/import/done'">Import</button></body></html>"""
MEDIUM_DONE = """<html><body><a href="https://medium.com/p/abc123/edit">See your story</a></body></html>"""
MEDIUM_EDITOR = """<html><body><button onclick="document.getElementById('d').style.display='block'">Publish</button>
<div id="d" style="display:none"><input placeholder="Add a topic...">
<button onclick="location.href='https://medium.com/@p/late-feedback-abc123'">Publish now</button></div></body></html>"""


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
    canonical_url="https://pankajads.github.io/writing/2026/10/late-feedback/",
)
SUB = RedditSubmission(subreddit="test", title="Why feedback fails", body="Body")


def test_reddit_submit_returns_comments_url(page):
    action = "location.href='https://old.reddit.com/r/test/comments/abc123/why/'"
    serve(
        page,
        {
            "https://old.reddit.com/r/test/submit": REDDIT_FORM.format(action=action),
            "https://old.reddit.com/r/test/comments/": "<html>ok</html>",
        },
    )
    assert reddit.submit(page, SUB, dry_run=False).endswith("/comments/abc123/why/")


def test_reddit_dry_run_fills_but_does_not_submit(page):
    serve(page, {"https://old.reddit.com/r/test/submit": REDDIT_FORM.format(action="location.href='/x'")})
    assert reddit.submit(page, SUB, dry_run=True) is None
    assert page.input_value('textarea[name="title"]') == "Why feedback fails"
    assert "/submit" in page.url


def test_reddit_rejection_surfaces_error_text(page):
    action = "document.querySelector('.error').style.display='inline'"
    serve(page, {"https://old.reddit.com/r/test/submit": REDDIT_FORM.format(action=action)})
    with pytest.raises(reddit.SubmitRejected, match="doing that too much"):
        reddit.submit(page, SUB, dry_run=False, timeout_ms=1500)


def test_reddit_login_redirect_detected(page):
    serve(
        page,
        {
            "https://old.reddit.com/r/test/submit": REDIRECT.format(to="https://old.reddit.com/login"),
            "https://old.reddit.com/login": "<html>login</html>",
        },
    )
    with pytest.raises(reddit.NotLoggedIn):
        reddit.submit(page, SUB, dry_run=True, timeout_ms=4000)


def test_medium_import_and_publish(page):
    serve(
        page,
        {
            "https://medium.com/p/import/done": MEDIUM_DONE,
            "https://medium.com/p/import": MEDIUM_IMPORT,
            "https://medium.com/p/abc123/edit": MEDIUM_EDITOR,
            "https://medium.com/@p/": "<html>published</html>",
        },
    )
    assert medium.publish(page, POST, dry_run=False) == "https://medium.com/@p/late-feedback-abc123"


def test_medium_dry_run_stops_before_import(page):
    serve(page, {"https://medium.com/p/import": MEDIUM_IMPORT})
    assert medium.publish(page, POST, dry_run=True) is None
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
        medium.publish(page, POST, dry_run=True, timeout_ms=4000)
