from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
POST_NAME_RE = re.compile(r"^(\d{4})-(\d{2})-(\d{2})-(.+)\.md$")


def split_front_matter(text: str) -> tuple[dict, str]:
    if not text.startswith("---\n"):
        raise ValueError("missing front matter")
    end = text.find("\n---", 4)
    if end == -1:
        raise ValueError("unterminated front matter")
    return yaml.safe_load(text[4:end]) or {}, text[end + 4 :].lstrip("\n")


@dataclass(frozen=True)
class Post:
    path: Path
    title: str
    date: date
    slug: str
    tags: list[str]
    canonical_url: str

    @property
    def key(self) -> str:
        return self.path.name


def site_base(root: Path = ROOT) -> str:
    cfg = yaml.safe_load((root / "_config.yml").read_text(encoding="utf-8"))
    return cfg["url"].rstrip("/") + "/" + cfg.get("baseurl", "").strip("/")


def load_post(path: Path, root: Path = ROOT) -> Post:
    m = POST_NAME_RE.match(path.name)
    if not m:
        raise ValueError(f"{path.name}: expected YYYY-MM-DD-slug.md")
    year, month, day, slug = m.groups()
    meta, _ = split_front_matter(path.read_text(encoding="utf-8"))
    return Post(
        path=path,
        title=meta["title"],
        date=date(int(year), int(month), int(day)),
        slug=slug,
        tags=list(meta.get("tags") or [])[:5],  # Medium accepts at most 5 topics
        canonical_url=f"{site_base(root)}/{year}/{month}/{slug}/",
    )
