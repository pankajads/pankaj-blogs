"""Submit a text post through old.reddit.com's submit form (a stable, plain HTML form).

New accounts may get a captcha, and some subreddits require flair; both fail the run with a
screenshot rather than retrying.
"""

from __future__ import annotations

import re

from playwright.sync_api import Page

from .post import RedditSubmission

SUBMIT_URL = "https://old.reddit.com/r/{sub}/submit?selftext=true"
TITLE = 'textarea[name="title"]'
TEXT = 'textarea[name="text"]'
SUBMIT = 'button[name="submit"]'
COMMENTS_URL_RE = re.compile(r"/comments/[a-z0-9]+")
ERROR = ".error:visible, .status.error:visible"


class NotLoggedIn(RuntimeError):
    pass


class SubmitRejected(RuntimeError):
    pass


def submit(page: Page, s: RedditSubmission, *, dry_run: bool, timeout_ms: int = 60_000) -> str | None:
    page.goto(SUBMIT_URL.format(sub=s.subreddit), wait_until="domcontentloaded")
    try:
        page.wait_for_selector(TITLE, timeout=timeout_ms // 4)
    except Exception:
        if "/login" in page.url:
            raise NotLoggedIn("Reddit session expired - run: python -m publisher login reddit") from None
        raise

    page.fill(TITLE, s.title)
    page.fill(TEXT, s.body)
    if dry_run:
        return None
    page.click(SUBMIT)
    try:
        page.wait_for_url(COMMENTS_URL_RE, timeout=timeout_ms)
    except Exception as exc:
        errors = page.locator(ERROR).all_inner_texts()
        raise SubmitRejected(f"r/{s.subreddit} rejected the post: {errors or exc}") from exc
    return page.url
