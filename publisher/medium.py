"""Create a Medium draft through its "Import a story" page. Never publishes.

Import (rather than typing into the editor) keeps formatting and sets the canonical link back
to the blog automatically. The author reviews the draft, adds topics and publishes by hand.

Selectors below were written without access to a live Medium session: if Medium changes its UI,
a run fails with a screenshot under the failures directory; fix the constant that broke.
"""

from __future__ import annotations

import re

from playwright.sync_api import Page

from .post import Post

IMPORT_URL = "https://medium.com/p/import"
URL_INPUT = 'input[type="url"], input[placeholder*="http" i], input[name*="url" i]'
IMPORT_BUTTON = re.compile(r"^\s*import\s*$", re.IGNORECASE)
AFTER_IMPORT_EDIT = re.compile(r"see your story|edit story|edit", re.IGNORECASE)
EDIT_URL_RE = re.compile(r"/p/[0-9a-f]+/edit")


class NotLoggedIn(RuntimeError):
    pass


def import_draft(page: Page, post: Post, *, dry_run: bool, timeout_ms: int = 60_000) -> str | None:
    """Return the draft's edit URL, or None on a dry run."""
    page.goto(IMPORT_URL, wait_until="domcontentloaded")
    try:
        page.wait_for_selector(URL_INPUT, timeout=timeout_ms // 4)
    except Exception:
        if "signin" in page.url or "login" in page.url:
            raise NotLoggedIn("Medium session expired - run: python -m publisher login medium") from None
        raise

    page.locator(URL_INPUT).first.fill(post.canonical_url)
    if dry_run:
        return None
    page.get_by_role("button", name=IMPORT_BUTTON).click()

    # Import finishes on a page linking to the new draft's editor.
    if not EDIT_URL_RE.search(page.url):
        page.get_by_role("link", name=AFTER_IMPORT_EDIT).first.click(timeout=timeout_ms)
    page.wait_for_url(EDIT_URL_RE, timeout=timeout_ms)
    return page.url
