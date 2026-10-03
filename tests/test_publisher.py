from datetime import date

import pytest

from publisher import __main__ as cli
from publisher import notify
from publisher.post import load_post
from publisher.state import State


@pytest.fixture
def site(tmp_path):
    (tmp_path / "_config.yml").write_text("url: https://pankajads.github.io\nbaseurl: /pankaj-blogs\n")
    (tmp_path / "_posts").mkdir()
    return tmp_path


def add_post(site, name="2026-10-05-late-feedback.md"):
    (site / "_posts" / name).write_text("---\ntitle: Late feedback\ntags: [leadership, management]\n---\nBody\n")
    return site / "_posts" / name


def test_canonical_url_matches_jekyll_permalink(site):
    post = load_post(add_post(site), site)
    assert post.canonical_url == "https://pankajads.github.io/pankaj-blogs/2026/10/late-feedback/"
    assert post.tags == ["leadership", "management"]


def test_pending_includes_future_dated_skips_old_and_finished_posts(site, tmp_path):
    add_post(site, "2026-10-05-a.md")
    add_post(site, "2026-10-20-future.md")
    add_post(site, "2026-01-01-old.md")
    state = State(tmp_path / "state.json")
    today = date(2026, 10, 6)
    assert [p.slug for p in cli.pending_posts(state, today, site)] == ["a", "future"]
    state.record("2026-10-20-future.md", "medium_draft", "u")
    state.record("2026-10-20-future.md", "notified", "t")

    state.record("2026-10-05-a.md", "medium_draft", "https://medium.com/p/abc/edit")
    assert [p.slug for p in cli.pending_posts(state, today, site)] == ["a"], "still owes an email"
    state.record("2026-10-05-a.md", "notified", "2026-10-06T09:00:00")
    assert cli.pending_posts(state, today, site) == []


def test_email_has_draft_link_and_no_publish_claim(site):
    post = load_post(add_post(site), site)
    msg = notify.build_message(post, "https://medium.com/p/abc/edit", "me@example.com", "me@example.com")
    body = msg.get_content()
    assert msg["Subject"] == "Medium draft ready to review: Late feedback"
    assert "https://medium.com/p/abc/edit" in body
    assert post.canonical_url + "?kit" in body
    assert "Nothing has been published" in body


def test_send_requires_smtp_config(site, monkeypatch):
    for var in ("SMTP_USER", "SMTP_PASSWORD", "NOTIFY_TO"):
        monkeypatch.delenv(var, raising=False)
    with pytest.raises(notify.NotConfigured):
        notify.send(load_post(add_post(site), site), "https://medium.com/p/abc/edit")


class FakePage:
    def close(self):
        pass


class FakeCtx:
    def new_page(self):
        return FakePage()


def test_draft_one_imports_once_and_retries_failed_email(site, tmp_path, monkeypatch):
    post = load_post(add_post(site), site)
    state = State(tmp_path / "state.json")
    imports, sent = [], []
    monkeypatch.setattr(cli, "wait_until_live", lambda url: None)
    monkeypatch.setattr(cli.medium, "import_draft", lambda page, p, dry_run: imports.append(p) or "https://m/p/1/edit")

    def failing_send(p, url):
        raise notify.NotConfigured("no smtp")

    monkeypatch.setattr(cli.notify, "send", failing_send)
    assert cli.draft_one(FakeCtx(), post, state, dry_run=False) is False
    assert state.get(post.key, "medium_draft") == "https://m/p/1/edit"

    monkeypatch.setattr(cli.notify, "send", lambda p, url: sent.append(url))
    assert cli.draft_one(FakeCtx(), post, state, dry_run=False) is True
    assert len(imports) == 1, "a second run must not import a duplicate draft"
    assert sent == ["https://m/p/1/edit"]


def test_state_persists(tmp_path):
    State(tmp_path / "s.json").record("p.md", "medium_draft", "u")
    assert State(tmp_path / "s.json").get("p.md", "medium_draft") == "u"
