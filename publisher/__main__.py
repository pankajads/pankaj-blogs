"""python -m publisher {login,publish,pending,publish-pending} ...

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

import yaml

from . import medium, reddit
from .post import ROOT, Post, load_post
from .state import State

HOME = Path(os.environ.get("PUBLISHER_HOME", Path.home() / ".writing-publisher"))
PROFILE = HOME / "profile"
FAILURES = HOME / "failures"
LOGIN_URLS = {"medium": "https://medium.com/m/signin", "reddit": "https://old.reddit.com/login"}
PENDING_WINDOW_DAYS = 14


def load_reddit_policy(root: Path = ROOT) -> dict:
    return yaml.safe_load((root / "reddit.yml").read_text(encoding="utf-8")) or {}


def allowed_reddit(post: Post, policy: dict, state: State, today: date) -> tuple[list, list[str]]:
    """Return (submissions allowed now, reasons for the ones skipped)."""
    allow = {s["name"].lower() for s in policy.get("subreddits") or []}
    limit = int(policy.get("max_subreddits_per_post", 1))
    gap = timedelta(days=int(policy.get("min_days_between_posts_per_subreddit", 14)))
    ok, skipped = [], []
    for s in post.reddit:
        last = state.get("_subreddit_last_post", s.subreddit.lower())
        if s.subreddit.lower() not in allow:
            skipped.append(f"r/{s.subreddit}: not in reddit.yml allowlist")
        elif len(ok) >= limit:
            skipped.append(f"r/{s.subreddit}: over max_subreddits_per_post={limit}")
        elif last and today - date.fromisoformat(last) < gap:
            skipped.append(f"r/{s.subreddit}: last posted {last}, minimum gap {gap.days}d")
        else:
            ok.append(s)
    return ok, skipped


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


def pending_posts(state: State, today: date, root: Path = ROOT) -> list[Post]:
    policy = load_reddit_policy(root)
    out = []
    for path in sorted((root / "_posts").glob("*.md")):
        post = load_post(path, root)
        if not (today - timedelta(days=PENDING_WINDOW_DAYS) <= post.date <= today):
            continue
        needs_medium = not state.get(post.key, "medium")
        allowed, _ = allowed_reddit(post, policy, state, today)
        needs_reddit = any(not state.get(post.key, f"reddit:{s.subreddit}") for s in allowed)
        if needs_medium or needs_reddit:
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


def publish_one(ctx, post: Post, state: State, *, only: str | None, dry_run: bool, today: date) -> bool:
    ok = True
    print(f"== {post.title}\n   {post.canonical_url}")
    if not dry_run:
        wait_until_live(post.canonical_url)

    page = ctx.new_page()
    try:
        if only in (None, "medium"):
            if state.get(post.key, "medium"):
                print(f"   medium: already published {state.get(post.key, 'medium')}")
            else:
                try:
                    url = medium.publish(page, post, dry_run=dry_run)
                    if url:
                        state.record(post.key, "medium", url)
                    print(f"   medium: {url or 'dry run ok (stopped before Import)'}")
                except Exception as exc:  # recorded with a screenshot; the run continues
                    ok = False
                    print(f"   medium: FAILED {exc}\n   evidence: {_save_failure(page, post.slug + '-medium')}")

        if only in (None, "reddit"):
            allowed, skipped = allowed_reddit(post, load_reddit_policy(), state, today)
            for reason in skipped:
                print(f"   reddit: skipped {reason}")
            for s in allowed:
                target = f"reddit:{s.subreddit}"
                if state.get(post.key, target):
                    print(f"   r/{s.subreddit}: already posted {state.get(post.key, target)}")
                    continue
                try:
                    url = reddit.submit(page, s, dry_run=dry_run)
                    if url:
                        state.record(post.key, target, url)
                        state.record("_subreddit_last_post", s.subreddit.lower(), today.isoformat())
                    print(f"   r/{s.subreddit}: {url or 'dry run ok (stopped before Submit)'}")
                except Exception as exc:  # recorded with a screenshot; the run continues
                    ok = False
                    evidence = _save_failure(page, f"{post.slug}-reddit")
                    print(f"   r/{s.subreddit}: FAILED {exc}\n   evidence: {evidence}")
    finally:
        page.close()
    return ok


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="publisher")
    sub = ap.add_subparsers(dest="cmd", required=True)
    lg = sub.add_parser("login", help="open a visible browser to log in once; the session is kept in the profile")
    lg.add_argument("site", choices=sorted(LOGIN_URLS))
    for name in ("publish", "publish-pending"):
        p = sub.add_parser(name)
        if name == "publish":
            p.add_argument("posts", nargs="+", type=Path)
        p.add_argument("--dry-run", action="store_true", help="fill forms but stop before the final click")
        p.add_argument("--only", choices=["medium", "reddit"])
        p.add_argument("--headed", action="store_true", help="show the browser (helps with bot checks)")
        p.add_argument("--channel", help="e.g. 'chrome' to use installed Google Chrome")
    sub.add_parser("pending", help="list posts that still need publishing")
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
            ctx.new_page().goto(LOGIN_URLS[args.site])
            input(f"Log in to {args.site} in the browser window, then press Enter here... ")
            ctx.close()
            return 0

        posts = [load_post(p.resolve()) for p in args.posts] if args.cmd == "publish" else pending_posts(state, today)
        if not posts:
            print("nothing to publish")
            return 0
        ctx = _context(pw, headed=args.headed, channel=args.channel)
        try:
            results = [publish_one(ctx, p, state, only=args.only, dry_run=args.dry_run, today=today) for p in posts]
        finally:
            ctx.close()
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
