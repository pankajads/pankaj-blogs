"""python -m publisher {login,draft,pending,draft-pending} ...

Creates Medium drafts (never publishes) and emails the author to review them.
Profile, state and failure screenshots live in $PUBLISHER_HOME (default ~/.writing-publisher),
never in the repository.
"""

from __future__ import annotations

import argparse
import os
import sys
import time
import urllib.request
from datetime import date, datetime, timedelta
from pathlib import Path

from . import medium, notify
from .post import ROOT, Post, load_post
from .state import State

HOME = Path(os.environ.get("PUBLISHER_HOME", Path.home() / ".writing-publisher"))
PROFILE = HOME / "profile"
FAILURES = HOME / "failures"
LOGIN_URL = "https://medium.com/m/signin"
PENDING_WINDOW_DAYS = 14


def wait_until_live(url: str, timeout_s: int = 900) -> None:
    deadline = time.monotonic() + timeout_s
    while True:
        try:
            with urllib.request.urlopen(url, timeout=20) as resp:
                if resp.status == 200:
                    return
        except Exception as exc:  # retried until the deadline, then surfaced
            if time.monotonic() > deadline:
                raise TimeoutError(f"{url} not live after {timeout_s}s: {exc}") from exc
        time.sleep(30)


def needs_work(post: Post, state: State) -> bool:
    return not state.get(post.key, "medium_draft") or not state.get(post.key, "notified")


def pending_posts(state: State, today: date, root: Path = ROOT) -> list[Post]:
    out = []
    for path in sorted((root / "_posts").glob("*.md")):
        post = load_post(path, root)
        recent = post.date >= today - timedelta(days=PENDING_WINDOW_DAYS)
        if recent and needs_work(post, state):
            out.append(post)
    return out


def _context(playwright, headed: bool, channel: str | None):
    PROFILE.mkdir(parents=True, exist_ok=True)
    os.chmod(HOME, 0o700)
    return playwright.chromium.launch_persistent_context(
        str(PROFILE), headless=not headed, channel=channel, viewport={"width": 1280, "height": 900}
    )


def _save_failure(page, label: str) -> Path:
    FAILURES.mkdir(parents=True, exist_ok=True)
    stem = FAILURES / f"{datetime.now():%Y%m%d-%H%M%S}-{label}"
    page.screenshot(path=f"{stem}.png", full_page=True)
    Path(f"{stem}.html").write_text(page.content(), encoding="utf-8")
    return stem


def draft_one(ctx, post: Post, state: State, *, dry_run: bool) -> bool:
    print(f"== {post.title}\n   {post.canonical_url}")
    draft_url = state.get(post.key, "medium_draft")
    if draft_url:
        print(f"   medium draft: already imported {draft_url}")
    else:
        if not dry_run:
            wait_until_live(post.canonical_url)
        page = ctx.new_page()
        try:
            draft_url = medium.import_draft(page, post, dry_run=dry_run)
        except Exception as exc:  # recorded with a screenshot; the run continues
            print(f"   medium draft: FAILED {exc}\n   evidence: {_save_failure(page, post.slug)}")
            return False
        finally:
            page.close()
        if not draft_url:
            print("   medium draft: dry run ok (stopped before Import)")
            return True
        state.record(post.key, "medium_draft", draft_url)
        print(f"   medium draft: {draft_url}")

    if state.get(post.key, "notified"):
        return True
    try:
        notify.send(post, draft_url)
    except Exception as exc:  # retried on the next run because 'notified' stays unset
        print(f"   email: FAILED {exc}")
        return False
    state.record(post.key, "notified", datetime.now().isoformat(timespec="seconds"))
    print("   email: sent")
    return True


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="publisher")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("login", help="open a visible browser to log in to Medium once; the session is kept")
    for name in ("draft", "draft-pending"):
        p = sub.add_parser(name)
        if name == "draft":
            p.add_argument("posts", nargs="+", type=Path)
        p.add_argument("--dry-run", action="store_true", help="fill the import form but stop before Import")
        p.add_argument("--headed", action="store_true", help="show the browser (helps with bot checks)")
        p.add_argument("--channel", help="e.g. 'chrome' to use installed Google Chrome")
    sub.add_parser("pending", help="list posts that still need a Medium draft or email")
    args = ap.parse_args(argv)

    state = State(HOME / "state.json")
    today = date.today()

    if args.cmd == "pending":
        for post in pending_posts(state, today):
            print(post.path.relative_to(ROOT))
        return 0

    from playwright.sync_api import sync_playwright

    with sync_playwright() as pw:
        if args.cmd == "login":
            ctx = _context(pw, headed=True, channel=None)
            ctx.new_page().goto(LOGIN_URL)
            input("Log in to Medium in the browser window, then press Enter here... ")
            ctx.close()
            return 0

        posts = [load_post(p.resolve()) for p in args.posts] if args.cmd == "draft" else pending_posts(state, today)
        if not posts:
            print("nothing to do")
            return 0
        ctx = _context(pw, headed=args.headed, channel=args.channel)
        try:
            results = [draft_one(ctx, p, state, dry_run=args.dry_run) for p in posts]
        finally:
            ctx.close()
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
