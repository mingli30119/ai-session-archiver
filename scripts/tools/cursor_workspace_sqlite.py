"""Cursor IDE chat panel (workspaceStorage SQLite).

Layout:
    %APPDATA%/Cursor/User/workspaceStorage/<hash>/state.vscdb     # SQLite DB
    %APPDATA%/Cursor/User/globalStorage/state.vscdb               # SQLite DB

Cursor stores legacy chat data in `cursorDiskKV` and `ItemTable` tables.
We export keys whose names look related to chat:
    - composerData:*        (newer composer threads)
    - workbench.panel.aichat.view.aichat.chatdata
    - aiService.prompts / aiService.generations
    - chatData / interactiveSessions

We also include the `workspace.json` next to the DB to record which working
directory this workspace points at.
"""

from __future__ import annotations

import json
import sqlite3
from contextlib import closing
from pathlib import Path
from typing import Iterable, Optional

from .base import (
    SessionFile,
    SessionRecord,
    ToolAdapter,
    appdata_roaming,
    safe_iterdir,
)


_INTERESTING_KEY_PREFIXES = (
    "composerData:",
    "bubbleId:",
    "messageRequestContext:",
)
_INTERESTING_KEYS = {
    "workbench.panel.aichat.view.aichat.chatdata",
    "aiService.prompts",
    "aiService.generations",
    "chat.preferences",
    "interactive.sessions",
}


def _peek_db_keys(db: Path) -> list[str]:
    """Return a list of chat-related keys actually present in the DB."""
    keys: list[str] = []
    if not db.exists():
        return keys
    try:
        with closing(sqlite3.connect(f"file:{db}?mode=ro", uri=True)) as conn:
            cur = conn.cursor()
            for table, key_col in [
                ("cursorDiskKV", "key"),
                ("ItemTable", "key"),
            ]:
                try:
                    cur.execute(f"SELECT {key_col} FROM {table}")
                    for (k,) in cur.fetchall():
                        if not isinstance(k, str):
                            continue
                        if k in _INTERESTING_KEYS or any(
                            k.startswith(p) for p in _INTERESTING_KEY_PREFIXES
                        ):
                            keys.append(f"{table}::{k}")
                except sqlite3.OperationalError:
                    continue
    except sqlite3.Error:
        return keys
    return keys


def export_db_chat_to_jsonl(db: Path, out_path: Path) -> int:
    """Write each chat-related row as one JSONL line. Returns row count."""
    if not db.exists():
        return 0
    out_path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with closing(sqlite3.connect(f"file:{db}?mode=ro", uri=True)) as conn, open(
        out_path, "w", encoding="utf-8"
    ) as fp:
        cur = conn.cursor()
        for table in ("cursorDiskKV", "ItemTable"):
            try:
                cur.execute(f"SELECT key, value FROM {table}")
            except sqlite3.OperationalError:
                continue
            for key, value in cur.fetchall():
                if not isinstance(key, str):
                    continue
                if not (
                    key in _INTERESTING_KEYS
                    or any(key.startswith(p) for p in _INTERESTING_KEY_PREFIXES)
                ):
                    continue
                if isinstance(value, (bytes, bytearray)):
                    try:
                        value_text = value.decode("utf-8")
                    except UnicodeDecodeError:
                        value_text = value.decode("utf-8", errors="replace")
                else:
                    value_text = value
                # Try to inline JSON when possible to keep one record per line.
                parsed = None
                if isinstance(value_text, str):
                    try:
                        parsed = json.loads(value_text)
                    except (json.JSONDecodeError, TypeError):
                        parsed = None
                record = {
                    "table": table,
                    "key": key,
                    "value_json": parsed,
                    "value_raw": None if parsed is not None else value_text,
                }
                fp.write(json.dumps(record, ensure_ascii=False) + "\n")
                count += 1
    return count


class CursorWorkspaceSqliteAdapter(ToolAdapter):
    """One SessionRecord per workspace state.vscdb that has chat-related rows."""

    id = "cursor-chat-sqlite"
    label = "Cursor IDE chat (workspaceStorage state.vscdb)"

    def default_roots(self) -> list[Path]:
        appdata = appdata_roaming()
        if appdata is None:
            return []
        roots: list[Path] = []
        for client in ("Cursor",):
            base = appdata / client / "User"
            if (base / "workspaceStorage").is_dir():
                roots.append(base / "workspaceStorage")
            if (base / "globalStorage").is_dir():
                roots.append(base / "globalStorage")
        return roots

    def discover(
        self, roots: Optional[list[Path]] = None
    ) -> Iterable[SessionRecord]:
        roots = roots or self.default_roots()
        for root in roots:
            if not root.exists():
                continue
            if root.name == "globalStorage":
                db = root / "state.vscdb"
                if db.exists() and _peek_db_keys(db):
                    yield SessionRecord(
                        tool=self.id,
                        session_id="_globalStorage",
                        project="_global",
                        files=[
                            SessionFile(
                                db,
                                role="main",
                                description="cursor globalStorage SQLite",
                                deletable=False,
                            )
                        ],
                        extra={"sqlite_export": True},
                    )
                continue
            for ws in safe_iterdir(root):
                if not ws.is_dir():
                    continue
                db = ws / "state.vscdb"
                if not db.exists():
                    continue
                keys = _peek_db_keys(db)
                if not keys:
                    continue
                files = [
                    SessionFile(
                        db,
                        role="main",
                        description="cursor workspace SQLite",
                        deletable=False,
                    )
                ]
                wsj = ws / "workspace.json"
                if wsj.is_file():
                    files.append(
                        SessionFile(
                            wsj,
                            role="meta",
                            description="workspace mapping",
                            deletable=False,
                        )
                    )
                yield SessionRecord(
                    tool=self.id,
                    session_id=ws.name,
                    project=ws.name,
                    files=files,
                    extra={"sqlite_export": True, "key_count": len(keys)},
                )
