# writing

My blog and publishing queue. A scheduled agent drafts a post every Monday and
Thursday and opens it as a pull request. **Nothing is published until I merge.**

- Blog: https://pankajads.github.io/writing/
- Original posts live here; Medium copies are imported with the link back to the original.

## How it works

```
publish-queue issues ──┐
                       ├─► scheduled agent (Mon + Thu) ─► draft PR ─► I edit + merge ─► GitHub Pages
stories/ (fallback) ───┘                                         │
                                                                 └─► Medium: "Import a story" (1 click)
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
4. **Publish** — merge the PR. GitHub Pages deploys it. The PR description has
   the Medium import step (medium.com/p/import → paste the post URL). Medium
   then credits this blog as the original.

## Rules the agent follows

See [`AGENT.md`](AGENT.md). In short: it never makes up a personal story, a quote or a
statistic. Every number links to a source the agent actually opened. It writes
in the voice of the samples in [`voice/`](voice/).

## What I need to keep feeding it

- `stories/` — real things that happened; 3–6 lines each is enough. Template in `stories/_TEMPLATE.md`.
- `voice/` — 3–5 pieces I actually wrote (posts, long emails, docs) so drafts sound like me.

## Local checks

```bash
pip install pyyaml pytest
python scripts/check_draft.py _posts/*.md
pytest -q
```
