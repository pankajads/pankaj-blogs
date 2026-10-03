"""Per-machine record of what has been published, so reruns never double-post."""

from __future__ import annotations

import json
from pathlib import Path


class State:
    def __init__(self, path: Path):
        self.path = path
        self.data: dict = json.loads(path.read_text()) if path.is_file() else {}

    def get(self, post_key: str, target: str) -> str | None:
        return self.data.get(post_key, {}).get(target)

    def record(self, post_key: str, target: str, url: str) -> None:
        self.data.setdefault(post_key, {})[target] = url
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.data, indent=2, sort_keys=True))
        tmp.replace(self.path)
