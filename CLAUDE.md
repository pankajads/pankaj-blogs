# CLAUDE.md

This repo is a personal blog plus a publishing queue.

- Scheduled drafting runs follow [`AGENT.md`](AGENT.md) exactly.
- **"Queue this" requests**: when asked to queue a topic, artifact or file, open a GitHub issue in
  `pankajads/writing` with the label `publish-queue`. The title is the working title. The body has
  the topic or angle, a link to the artifact or file (or its pasted content), and any notes on audience or length.
  Don't draft the post at queue time.
- Draft Reddit versions only for subreddits listed in `reddit.yml`.
- Never push to `main`. Never merge draft PRs; the author does.
- Never add a personal anecdote, quote or statistic that isn't backed by `stories/` or by a
  source you opened (see AGENT.md §3).
