"""Claude Code per-project sessions.

Layout:
    ~/.claude/projects/<project-name>/<session-uuid>.jsonl       # main session
    ~/.claude/projects/<project-name>/<session-uuid>/subagents/  # optional sub-agents
        agent-<id>.jsonl
        agent-<id>.meta.json
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterable, Optional

from .base import SessionFile, SessionRecord, ToolAdapter, home, safe_iterdir


class ClaudeCodeAdapter(ToolAdapter):
    id = "claude-code"
    label = "Claude Code (~/.claude/projects)"

    def default_roots(self) -> list[Path]:
        root = home() / ".claude" / "projects"
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

                main_jsonls = sorted(
                    p for p in safe_iterdir(project_dir) if p.suffix == ".jsonl"
                )
                # Map session_id -> SessionRecord
                by_id: dict[str, SessionRecord] = {}
                for main in main_jsonls:
                    sid = main.stem
                    rec = SessionRecord(
                        tool=self.id,
                        session_id=sid,
                        project=project_dir.name,
                        files=[
                            SessionFile(main, role="main", description="claude-code session")
                        ],
                    )
                    by_id[sid] = rec

                # Pick up subagent folders (named <session-uuid>/subagents/)
                for child in safe_iterdir(project_dir):
                    if not child.is_dir():
                        continue
                    sub_dir = child / "subagents"
                    if not sub_dir.is_dir():
                        continue
                    sid = child.name
                    rec = by_id.get(sid)
                    if rec is None:
                        # subagents-only session (no main jsonl)
                        rec = SessionRecord(
                            tool=self.id,
                            session_id=sid,
                            project=project_dir.name,
                            files=[],
                        )
                        by_id[sid] = rec
                    for sub in safe_iterdir(sub_dir):
                        if sub.suffix == ".jsonl":
                            rec.files.append(
                                SessionFile(
                                    sub, role="subagent", description="subagent transcript"
                                )
                            )
                        elif sub.suffix == ".json":
                            rec.files.append(
                                SessionFile(
                                    sub, role="meta", description="subagent metadata"
                                )
                            )

                for rec in by_id.values():
                    if rec.files:
                        yield rec
