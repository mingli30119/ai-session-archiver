"""Cursor IDE per-project agent transcripts.

Layout:
    ~/.cursor/projects/<project-id>/agent-transcripts/<session-uuid>/
        <session-uuid>.jsonl                 # main transcript (JSONL, one event per line)
        subagents/<subagent-uuid>.jsonl       # zero or more sub-agents

The main transcript is the canonical source of truth and contains the full
event stream: user input, assistant output, thinking, tool calls and results.
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterable, Optional

from .base import SessionFile, SessionRecord, ToolAdapter, home, safe_iterdir


class CursorAgentAdapter(ToolAdapter):
    id = "cursor"
    label = "Cursor IDE (per-project agent transcripts)"

    def default_roots(self) -> list[Path]:
        root = home() / ".cursor" / "projects"
        return [root] if root.exists() else []

    def discover(
        self, roots: Optional[list[Path]] = None
    ) -> Iterable[SessionRecord]:
        roots = roots or self.default_roots()
        for projects_root in roots:
            if not projects_root.exists():
                continue
            for project_dir in safe_iterdir(projects_root):
                if not project_dir.is_dir():
                    continue
                transcripts_dir = project_dir / "agent-transcripts"
                if not transcripts_dir.is_dir():
                    continue
                for session_dir in safe_iterdir(transcripts_dir):
                    if not session_dir.is_dir():
                        continue
                    main = session_dir / f"{session_dir.name}.jsonl"
                    files: list[SessionFile] = []
                    if main.exists():
                        files.append(
                            SessionFile(main, role="main", description="agent transcript")
                        )
                    sub_dir = session_dir / "subagents"
                    if sub_dir.is_dir():
                        for sub in safe_iterdir(sub_dir):
                            if sub.suffix == ".jsonl":
                                files.append(
                                    SessionFile(
                                        sub,
                                        role="subagent",
                                        description="subagent transcript",
                                    )
                                )
                    if not files:
                        continue
                    rec = SessionRecord(
                        tool=self.id,
                        session_id=session_dir.name,
                        project=project_dir.name,
                        files=files,
                    )
                    yield rec
