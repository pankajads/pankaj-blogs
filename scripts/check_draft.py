"""Reject drafts with unsourced figures, unbacked personal anecdotes, or AI-tell phrasing.

Usage: python scripts/check_draft.py _posts/2026-10-05-some-post.md [...]
Exits non-zero and prints one line per problem if any check fails.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
STORIES = ROOT / "stories"

REQUIRED_FIELDS = ("title", "date", "origin")

# Phrases that read as generated filler. Matched case-insensitively on word boundaries.
BANNED_PHRASES = (
    "delve",
    "in today's fast-paced",
    "in today’s fast-paced",
    "it's important to note",
    "it is important to note",
    "tapestry",
    "game-changer",
    "game changer",
    "navigate the complexities",
    "in conclusion",
    "unlock the power",
    "unleash",
    "a testament to",
    "ever-evolving",
    "let's dive in",
    "without further ado",
    "at the end of the day",
    "in the realm of",
    "embark on a journey",
    "paradigm shift",
    "synergy",
)

# A paragraph containing a statistic must carry a link or footnote in that same paragraph.
STAT_RE = re.compile(
    r"\b\d+(?:\.\d+)?\s?(?:%|percent\b|x\b|times\b)"
    r"|\b\d+\s+(?:out\s+of|in)\s+(?:every\s+)?\d+\b"
    r"|\b(?:study|survey|research|report)\s+(?:found|shows|showed|suggests)\b",
    re.IGNORECASE,
)
LINK_RE = re.compile(r"\]\(https?://|\[\^[^\]]+\]")

# First-person anecdote markers: these require a `story:` from the story bank.
ANECDOTE_RE = re.compile(
    r"\bI (?:remember|recall|once)\b"
    r"|\b(?:years|months) ago\b"
    r"|\bwhen I (?:was|joined|took over|started)\b"
    r"|\b(?:one of my|a member of my|someone on my) (?:reports|team|engineers|directs)\b"
    r"|\bmy (?:first|old|former) (?:manager|boss|team|company)\b",
    re.IGNORECASE,
)

MAX_EM_DASH_PER_100_WORDS = 1.0


def split_front_matter(text: str) -> tuple[dict, str]:
    if not text.startswith("---\n"):
        raise ValueError("missing front matter")
    end = text.find("\n---", 4)
    if end == -1:
        raise ValueError("unterminated front matter")
    meta = yaml.safe_load(text[4:end]) or {}
    return meta, text[end + 4 :]


def check(path: Path) -> list[str]:
    try:
        meta, body = split_front_matter(path.read_text(encoding="utf-8"))
    except (ValueError, yaml.YAMLError) as exc:
        return [f"{path}: {exc}"]

    errors: list[str] = []
    for field in REQUIRED_FIELDS:
        if not meta.get(field):
            errors.append(f"{path}: front matter missing '{field}'")

    story = meta.get("story")
    if story and not (STORIES / f"{story}.md").is_file():
        errors.append(f"{path}: story '{story}' not found in stories/")

    for src in meta.get("sources") or []:
        if not isinstance(src, dict) or not str(src.get("url", "")).startswith("http"):
            errors.append(f"{path}: every sources entry needs an http(s) url")
        elif not src.get("supports"):
            errors.append(f"{path}: source {src['url']} has no 'supports' claim")

    # Ignore fenced code when scanning prose.
    prose = re.sub(r"```.*?```", "", body, flags=re.DOTALL)
    lowered = prose.lower()

    for phrase in BANNED_PHRASES:
        if re.search(rf"(?<!\w){re.escape(phrase)}", lowered):
            errors.append(f"{path}: AI-tell phrase '{phrase}' — rewrite the sentence")

    for n, para in enumerate(re.split(r"\n\s*\n", prose), start=1):
        if STAT_RE.search(para) and not LINK_RE.search(para):
            snippet = " ".join(para.split())[:80]
            errors.append(f"{path}: paragraph {n} has a figure/study with no source link: '{snippet}…'")
        if not story and ANECDOTE_RE.search(para):
            snippet = " ".join(para.split())[:80]
            errors.append(
                f"{path}: paragraph {n} reads as a personal anecdote but no 'story:' is set: '{snippet}…'"
            )

    words = len(prose.split())
    dashes = prose.count("—")
    if words and dashes / words * 100 > MAX_EM_DASH_PER_100_WORDS:
        errors.append(f"{path}: {dashes} em dashes in {words} words — too many, restructure sentences")

    return errors


def main(argv: list[str]) -> int:
    errors = [e for arg in argv for e in check(Path(arg))]
    for e in errors:
        print(e)
    if not errors:
        print(f"ok: {len(argv)} file(s)")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
