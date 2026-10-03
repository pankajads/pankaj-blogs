# writing

My blog and publishing queue. A scheduled agent drafts a post every Monday and
Thursday and opens it as a pull request. **Nothing is published until I merge.**

- Blog: https://pankajads.github.io/writing/
- Original posts live here; Medium copies are imported with the link back to the original.

## How it works

```
publish-queue issues ──┐                                   (cloud)                       (my machine)
                       ├─► scheduled agent (Mon + Thu) ─► draft PR ─► I merge ─► Pages ─► publisher (Playwright)
stories/ (fallback) ───┘     post + optional _reddit/ version                              ├─► Medium (import page)
                                                                                           └─► Reddit (old.reddit form)
```

1. **Queue** — open an issue with the `publish-queue` label (template: *Queue a post*).
   Put a topic, an outline, or a link to an artifact/file in it. From any Claude
   session you can also say: *"queue this in pankajads/writing"*.
2. **Draft** — the agent takes the oldest queued issue. If the queue is empty it
   writes a people-management / leadership post from an **unused story in
   [`stories/`](stories/)**. If there are no unused stories, it opens an issue
   asking me for one instead of inventing anything.
3. **Check** — `scripts/check_draft.py` runs on every draft PR: figures with no source,
   personal stories that aren't in the story bank, and common AI phrases all fail the PR.
4. **Publish** — merge the PR. GitHub Pages deploys it. Then the local publisher
   (`scripts/publish-local.sh`, run by cron on my machine) uses a logged-in browser to:
   - **Medium**: open medium.com/p/import, import the post URL (formatting is kept and
     the canonical link points to this blog), add tags and publish.
   - **Reddit**: submit the `_reddit/` text version to the approved subreddit via old.reddit.com.
     Only subreddits in `reddit.yml` are allowed, by default 1 per post and 14 days apart.

## Publisher setup (once, on my machine)

```bash
git clone https://github.com/pankajads/writing && cd writing
python3 -m pip install -r requirements.txt && python3 -m playwright install chromium
python3 -m publisher login medium        # log in by hand in the window, press Enter
python3 -m publisher login reddit
scripts/publish-local.sh --dry-run --headed   # fills the forms, stops before the final click
# then schedule it, e.g. crontab:  17 */2 * * * /path/to/writing/scripts/publish-local.sh
```

Browser sessions, state (`state.json`, prevents double posts) and failure screenshots live in
`~/.writing-publisher/`, never in the repo. If a site changes its UI, the run fails with a screenshot
in `failures/`; fix the selector constant at the top of `publisher/medium.py` or `publisher/reddit.py`.
If you get `NotLoggedIn`, run `login` again.

## Rules the agent follows

See [`AGENT.md`](AGENT.md). In short: it never makes up a personal story, a quote or a
statistic. Every number links to a source the agent actually opened. It writes
in the voice of the samples in [`voice/`](voice/).

## What I need to keep feeding it

- `stories/` — real things that happened; 3–6 lines each is enough. Template in `stories/_TEMPLATE.md`.
- `voice/` — 3–5 pieces I actually wrote (posts, long emails, docs) so drafts sound like me.

## Local checks

```bash
pip install -r requirements.txt ruff && python -m playwright install chromium
python scripts/check_draft.py _posts/*.md
ruff check . && pytest -q
```
