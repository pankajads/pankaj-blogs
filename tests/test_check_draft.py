import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import check_draft  # noqa: E402

GOOD_BODY = (
    "Most feedback fails because it arrives late.\n\n"
    "Gallup reports that 23% of employees strongly agree their manager gives meaningful feedback "
    "([Gallup](https://www.gallup.com/workplace/)).\n"
)


def write(tmp_path, front, body):
    p = tmp_path / "post.md"
    p.write_text(f"---\n{front}---\n{body}", encoding="utf-8")
    return p


def test_clean_post_passes(tmp_path):
    p = write(tmp_path, "title: T\ndate: 2026-10-05\norigin: issue#1\n", GOOD_BODY)
    assert check_draft.check(p) == []


def test_unsourced_statistic_fails(tmp_path):
    p = write(tmp_path, "title: T\ndate: 2026-10-05\norigin: issue#1\n", "70% of managers never get trained.\n")
    assert any("no source link" in e for e in check_draft.check(p))


def test_anecdote_without_story_fails(tmp_path):
    p = write(tmp_path, "title: T\ndate: 2026-10-05\norigin: issue#1\n", "I remember my first reorg.\n")
    assert any("personal anecdote" in e for e in check_draft.check(p))


def test_unknown_story_fails(tmp_path):
    p = write(tmp_path, "title: T\ndate: 2026-10-05\norigin: x\nstory: does-not-exist\n", "Fine.\n")
    assert any("not found in stories" in e for e in check_draft.check(p))


def test_banned_phrase_fails(tmp_path):
    p = write(tmp_path, "title: T\ndate: 2026-10-05\norigin: x\n", "Let us delve into hiring.\n")
    assert any("delve" in e for e in check_draft.check(p))


def test_missing_front_matter_fails(tmp_path):
    p = tmp_path / "post.md"
    p.write_text("no front matter", encoding="utf-8")
    assert check_draft.check(p)


def test_source_without_supports_fails(tmp_path):
    front = "title: T\ndate: 2026-10-05\norigin: x\nsources:\n  - url: https://example.com\n"
    p = write(tmp_path, front, "Fine.\n")
    assert any("supports" in e for e in check_draft.check(p))


def test_reddit_file_must_target_allowlisted_sub(tmp_path, monkeypatch):
    (tmp_path / "reddit.yml").write_text("max_subreddits_per_post: 1\nsubreddits:\n  - name: ExperiencedDevs\n")
    monkeypatch.setattr(check_draft, "ROOT", tmp_path)
    good = tmp_path / "good.md"
    good.write_text("---\nsubmissions:\n  - subreddit: experienceddevs\n    title: T\n---\nBody\n")
    bad = tmp_path / "bad.md"
    bad.write_text(
        "---\nsubmissions:\n  - subreddit: startups\n    title: T\n  - subreddit: ExperiencedDevs\n---\nBody\n"
    )
    assert check_draft.check_reddit(good) == []
    errors = check_draft.check_reddit(bad)
    assert any("not in reddit.yml" in e for e in errors)
    assert any("max_subreddits_per_post" in e for e in errors)
    assert any("no title" in e for e in errors)
