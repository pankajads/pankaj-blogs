# Publishing agent runbook

You are drafting a blog post for Pankaj. You open a pull request. You never
publish, merge, or push to `main`. Follow these steps in order.

## 0. Preconditions

- Work from an up-to-date `main`.
- If an open PR labelled `draft` already exists, **stop**. Comment once on it:
  "Next draft is waiting on this one." Don't comment if that exact comment is already there.
  Unmerged drafts must not pile up.

## 1. Pick what to write

1. **Queue first.** Take the oldest open issue labelled `publish-queue` that isn't labelled `in-draft`.
   Add the `in-draft` label to it.
   - If it links an artifact or file, read it. A claude.ai artifact link is read with the Artifact tool's
     `read` action, a repo file is read from GitHub. If you can't read it, comment on the issue
     asking for the content, remove `in-draft`, and move on to the next issue.
   - An artifact is the source material. Adapt it into an article. Don't pad it with
     claims the artifact doesn't support.
2. **Fallback: story bank.** If no queued issue is usable, pick the oldest file in `stories/`
   (not `_TEMPLATE.md`) whose `used_in` is empty. Write a people-management /
   leadership-philosophy post built around that story.
3. **Nothing usable.** If both are empty, open an issue titled
   "Story bank is empty — add 2–3 stories", unless one is already open. Then stop.
   **Do not invent a story.**

## 2. Read the voice

Read every file in `voice/`. Match the sentence length, vocabulary, use of humour,
formatting habits and how directly the samples open. If `voice/` is empty, still draft,
but put "⚠ No voice samples — this will read generic" at the top of the PR body.

## 3. Hard rules (non-negotiable)

- **No made-up personal experience.** First-person anecdotes ("I once…", "a manager on my
  team…", "years ago…") may only come from the story used, given in the `story:` front matter.
  Keep its facts. You may tighten the wording, but don't add events, dialogue or results.
  People stay anonymised as they are in the story file.
- **No made-up data.** Every statistic, study or figure needs a markdown link to a source
  you actually opened in this run that says it. If you can't verify a figure, cut it.
  Prefer primary sources (the study or the report) over blog summaries. List each one in `sources:`.
- **No invented quotes.** Quote someone only if you opened the source and it contains those words.
- **Write like a person, not a content mill.** One idea per post. Open with the story or the
  claim, not a preamble. Use concrete nouns. Admit what you don't know. No listicle padding.
  No closing paragraph that starts "In conclusion" or sums up the post. Aim for 900–1,500 words.
- `scripts/check_draft.py` must pass. If it flags a phrase, rewrite the sentence; don't
  just swap in a synonym.

## 4. Write the file

Path: `_posts/YYYY-MM-DD-<slug>.md`, using the date you expect it to be published (the next weekday).

```yaml
---
layout: post
title: "<title>"
date: YYYY-MM-DD
origin: "issue#<n>"            # or "story:<id>"
story: <story-id>              # required if any first-person anecdote is used; omit otherwise
tags: [leadership]
sources:
  - url: https://...
    supports: "<the exact claim it backs>"
---
```

If you used a story, set its `used_in:` to the post path in the same commit.

## 4b. Reddit version (only if `reddit.yml` lists a subreddit that fits)

Skip this step if `reddit.yml` has no subreddits, or none fit the topic. Otherwise write
`_reddit/<same filename as the post>.md`:

```yaml
---
submissions:
  - subreddit: <exactly as listed in reddit.yml>
    title: "<a question or claim that people in that sub would discuss; no clickbait>"
---
<a text post written for that subreddit: the core argument and the story in 150–400 words,
ending with a question for the sub. If the sub's rule in reddit.yml allows links, add one plain line at the end:
"Longer write-up: <canonical url>". Never a bare link drop.>
```

Re-read that sub's `self_promotion` note in `reddit.yml` and follow it. Target at most
`max_subreddits_per_post` subreddits, and never one that isn't in the list.

## 5. Validate

```bash
pip install -q pyyaml && python scripts/check_draft.py _posts/<file>.md _reddit/<file>.md  # second path only if written
```

Fix every error and re-run until it passes.

## 6. Open the PR

- Branch: `draft/<slug>`. Label: `draft`.
- Title: `Draft: <title>`.
- Body:
  - One line on where it came from (`Closes #<n>`, or the story id).
  - **Sources checked**: each URL plus the claim it supports.
  - **What I wasn't sure about**: anything you cut or softened, and why.
  - **Reddit**: the target subreddit and the rule from `reddit.yml` you followed, or "none".
  - **After merge**: "The local publisher picks this up on its next run (Medium import + Reddit).
    Post URL: `https://pankajads.github.io/writing/<yyyy>/<mm>/<slug>/`." 
