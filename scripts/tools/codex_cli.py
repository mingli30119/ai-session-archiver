"""Codex CLI rollouts.

Layout:
    ~/.codex/sessions/<YYYY>/<MM>/<DD>/rollout-<ts>-<uuid>.jsonl
    ~/.codex/session_index.jsonl                         # global index (one line per session)
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Iterable, Optional

from .base import SessionFile, SessionRecord, ToolAdapter, home


_FNAME_RE = re.compile(
    r"^rollout-(\d{4})-(\d{2})-(\d{2})T(\d{2})-(\d{2})-(\d{2})-([0-9a-f-]+)\.jsonl$",
    re.IGNORECASE,
)


class CodexCliAdapter(ToolAdapter):
    id = "codex"
    label = "Codex CLI (~/.codex/sessions)"

    def default_roots(self) -> list[Path]:
        root = home() / ".codex" / "sessions"
        return [root] if root.exists() else []

    def discover(
        self, roots: Optional[list[Path]] = None
    ) -> Iterable[SessionRecord]:
        roots = roots or self.default_roots()
        for root in roots:
            if not root.exists():
                continue
            for path in root.rglob("rollout-*.jsonl"):
                if not path.is_file():
                    continue
                m = _FNAME_RE.match(path.name)
                if m:
                    session_id = m.group(7)
                else:
                    session_id = path.stem
                yield SessionRecord(
                    tool=self.id,
                    session_id=session_id,
                    project=None,
                    files=[
                        SessionFile(path, role="main", description="codex rollout")
                    ],
                )
