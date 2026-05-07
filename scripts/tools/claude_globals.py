"""Claude Code global session metadata and input history.

These are NOT full conversation transcripts (those live in projects/), but
still useful to archive for completeness:
    ~/.claude/sessions/<pid>.json   # per-process session metadata
    ~/.claude/history.jsonl         # global user input history
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterable, Optional

from .base import SessionFile, SessionRecord, ToolAdapter, home, safe_iterdir


class ClaudeGlobalsAdapter(ToolAdapter):
    id = "claude-globals"
    label = "Claude Code globals (~/.claude/sessions, ~/.claude/history.jsonl)"

    def default_roots(self) -> list[Path]:
        root = home() / ".claude"
        return [root] if root.exists() else []

    def discover(
        self, roots: Optional[list[Path]] = None
    ) -> Iterable[SessionRecord]:
        roots = roots or self.default_roots()
        for root in roots:
            if not root.exists():
                continue
            sessions_dir = root / "sessions"
            if sessions_dir.is_dir():
                for path in safe_iterdir(sessions_dir):
                    if path.suffix == ".json" and path.is_file():
                        yield SessionRecord(
                            tool=self.id,
                            session_id=f"sessions-{path.stem}",
                            project="_global",
                            files=[
                                SessionFile(path, role="meta", description="session metadata")
                            ],
                        )
            history = root / "history.jsonl"
            if history.is_file():
                yield SessionRecord(
                    tool=self.id,
                    session_id="history",
                    project="_global",
                    files=[
                        SessionFile(history, role="history", description="user input history")
                    ],
                )
