"""Cline (saoudrizwan.claude-dev) VSCode extension tasks.

Layout:
    %APPDATA%/Code/User/globalStorage/saoudrizwan.claude-dev/tasks/<ts-id>/
        api_conversation_history.json   # raw API messages (full content)
        ui_messages.json                # UI rendered messages
        task_metadata.json              # metadata
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterable, Optional

from .base import (
    SessionFile,
    SessionRecord,
    ToolAdapter,
    appdata_roaming,
    safe_iterdir,
)


class ClineVscodeAdapter(ToolAdapter):
    id = "cline-vscode"
    label = "Cline VSCode extension (saoudrizwan.claude-dev/tasks)"

    def default_roots(self) -> list[Path]:
        roots: list[Path] = []
        appdata = appdata_roaming()
        if appdata is not None:
            for client in ("Code", "Code - Insiders", "Cursor"):
                p = (
                    appdata
                    / client
                    / "User"
                    / "globalStorage"
                    / "saoudrizwan.claude-dev"
                    / "tasks"
                )
                if p.exists():
                    roots.append(p)
        return roots

    def discover(
        self, roots: Optional[list[Path]] = None
    ) -> Iterable[SessionRecord]:
        roots = roots or self.default_roots()
        for tasks_root in roots:
            if not tasks_root.exists():
                continue
            for task_dir in safe_iterdir(tasks_root):
                if not task_dir.is_dir():
                    continue
                files: list[SessionFile] = []
                api = task_dir / "api_conversation_history.json"
                ui = task_dir / "ui_messages.json"
                meta = task_dir / "task_metadata.json"
                if api.is_file():
                    files.append(
                        SessionFile(api, role="api", description="raw API conversation")
                    )
                if ui.is_file():
                    files.append(SessionFile(ui, role="ui", description="UI messages"))
                if meta.is_file():
                    files.append(SessionFile(meta, role="meta", description="task metadata"))
                if not files:
                    continue
                yield SessionRecord(
                    tool=self.id,
                    session_id=task_dir.name,
                    project=tasks_root.parts[-5] if len(tasks_root.parts) >= 5 else None,
                    files=files,
                )
