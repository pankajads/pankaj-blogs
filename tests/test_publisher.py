from datetime import date

import pytest

from publisher import __main__ as cli
from publisher.post import load_post
from publisher.state import State


@pytest.fixture
def site(tmp_path):
    (tmp_path / "_config.yml").write_text("url: https://pankajads.github.io\nbaseurl: /writing\n")
    (tmp_path / "_posts").mkdir()
    (tmp_path / "_reddit").mkdir()
    (tmp_path / "reddit.yml").write_text(
        "max_subreddits_per_post: 1\nmin_days_between_posts_per_subreddit: 14\nsubreddits:\n  - name: ExperiencedDevs\n"
    )
    return tmp_path


def add_post(site, name="2026-10-05-late-feedback.md", reddit_subs=()):
    (site / "_posts" / name).write_text("---\ntitle: Late feedback\ntags: [leadership, management]\n---\nBody\n")
    if reddit_subs:
        subs = "".join(f"  - subreddit: {s}\n    title: Why feedback fails\n" for s in reddit_subs)
        (site / "_reddit" / name).write_text(f"---\nsubmissions:\n{subs}---\nReddit body\n")
    return site / "_posts" / name


def test_canonical_url_matches_jekyll_permalink(site):
    post = load_post(add_post(site), site)
    assert post.canonical_url == "https://pankajads.github.io/writing/2026/10/late-feedback/"
    assert post.tags == ["leadership", "management"]


def test_reddit_body_and_submissions_loaded(site):
    post = load_post(add_post(site, reddit_subs=["ExperiencedDevs"]), site)
    assert post.reddit[0].subreddit == "ExperiencedDevs"
    assert post.reddit[0].body == "Reddit body"


def test_reddit_allowlist_limit_and_gap(site, tmp_path):
    post = load_post(add_post(site, reddit_subs=["ExperiencedDevs", "managers", "ExperiencedDevs"]), site)
    policy = cli.load_reddit_policy(site)
    state = State(tmp_path / "state.json")
    ok, skipped = cli.allowed_reddit(post, policy, state, date(2026, 10, 5))
    assert [s.subreddit for s in ok] == ["ExperiencedDevs"]
    assert any("not in reddit.yml" in r for r in skipped)
    assert any("max_subreddits_per_post" in r for r in skipped)

    state.record("_subreddit_last_post", "experienceddevs", "2026-10-01")
    ok, skipped = cli.allowed_reddit(post, policy, state, date(2026, 10, 5))
    assert ok == [] and any("minimum gap" in r for r in skipped)


def test_pending_skips_published_future_and_old_posts(site, tmp_path):
    add_post(site, "2026-10-05-a.md")
    add_post(site, "2026-10-20-future.md")
    add_post(site, "2026-01-01-old.md")
    state = State(tmp_path / "state.json")
    today = date(2026, 10, 6)
    assert [p.slug for p in cli.pending_posts(state, today, site)] == ["a"]
    state.record("2026-10-05-a.md", "medium", "https://medium.com/@p/a")
    assert cli.pending_posts(state, today, site) == []


def test_state_persists(tmp_path):
    State(tmp_path / "s.json").record("p.md", "medium", "u")
    assert State(tmp_path / "s.json").get("p.md", "medium") == "u"
