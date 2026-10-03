# pankaj-blogs

My blog and publishing queue. A scheduled agent drafts a post every Monday and
Thursday and opens it as a pull request. **Nothing goes out until I merge, and
nothing is published on Medium or Reddit without me pressing the button.**

- Blog: https://pankajads.github.io/pankaj-blogs/
- Posts live here first. Medium copies are imported as **drafts** that link back to the original.

## How it works

```
publish-queue issues ──┐                (cloud)                          (my machine, cron)
                       ├─► agent, Mon + Thu ─► draft PR ─► I merge ─► Pages ─► Medium draft ─► email to me
stories/ (fallback) ───┘                                                               │
                                                                     I review + publish on Medium
                                                          Reddit: I copy from the post page (?kit) and post
```

1. **Queue**: open an issue with the `publish-queue` label (template: *Queue a post*).
   Put in a topic, an outline, or a link to an artifact or file. From any Claude session you
   can also say: *"queue this in pankajads/pankaj-blogs"*.
2. **Draft**: the agent takes the oldest queued issue. If the queue is empty, it writes a
   people-management / leadership post from an **unused story in [`stories/`](stories/)**.
   If there are no unused stories, it opens an issue asking me for one instead of inventing anything.
3. **Check**: `scripts/check_draft.py` runs on every draft PR. It fails the PR on figures with no source,
   on personal stories that aren't in the story bank, and on common AI phrases.
4. **Merge**: GitHub Pages deploys the post.
5. **Medium draft + email**: the local publisher (`scripts/publish-local.sh`) imports the post into
   Medium through medium.com/p/import. That keeps the formatting and sets the canonical link to this
   blog. It **stops at draft** and emails me the draft link. I add topics and publish by hand.
6. **Reddit (manual)**: open the post with `?kit` on the end of its URL. The share kit shows the
   suggested subreddit, a title and a Markdown body, each with a copy button.

## The post page

- Serif reading layout, light and dark mode, reading-progress bar, a reading-time estimate and a sources list.
- **Copy article**: rich text (headings, bold, links) for Medium, Google Docs or email.
- **Copy as Markdown**: for Reddit, GitHub or any Markdown editor.
- **Copy link**: the canonical URL.
- Selecting text by hand also copies clean prose. Decorations are CSS-only, and the buttons sit outside the article.
- `?kit` shows the Reddit share kit (from `_reddit/<post filename>`). Regular readers don't see it.

## Publisher setup (once, on my machine)

```bash
git clone https://github.com/pankajads/pankaj-blogs && cd pankaj-blogs
python3 -m pip install -r requirements.txt && python3 -m playwright install chromium
python3 -m publisher login                  # log in to Medium by hand in the window, press Enter

# Email: create a Gmail app password (Google Account → Security → 2-Step Verification → App passwords)
mkdir -p ~/.writing-publisher && cat > ~/.writing-publisher/smtp.env <<'ENV'
SMTP_USER=pankajads@gmail.com
SMTP_PASSWORD=<16-character app password>
NOTIFY_TO=pankajads@gmail.com
ENV
chmod 600 ~/.writing-publisher/smtp.env

scripts/publish-local.sh --dry-run --headed  # fills the import form, stops before Import
# then schedule it, e.g. crontab:  17 */2 * * * /path/to/pankaj-blogs/scripts/publish-local.sh
```

The Medium session, `state.json` (which stops duplicate drafts and emails) and failure screenshots
all live in `~/.writing-publisher/`, never in the repo. If Medium changes its UI, the run fails with a
screenshot in `failures/`. Fix the selector constant at the top of `publisher/medium.py`. If you get
`NotLoggedIn`, run `login` again. If the email fails, the next run retries it without importing a second draft.

## What I need to keep feeding it

- `stories/`: real things that happened; 3–6 lines each is enough. The template is in `stories/_TEMPLATE.md`.
- `voice/`: 3–5 pieces I actually wrote (posts, long emails, docs), so drafts sound like me.
- `reddit.yml`: subreddits I'm happy to post in, with each one's self-promotion rule.

## Local checks

```bash
pip install -r requirements.txt ruff && python -m playwright install chromium
python scripts/check_draft.py _posts/*.md
ruff check . && pytest -q
```
