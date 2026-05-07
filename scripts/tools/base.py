"""Common types for tool adapters."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Optional


@dataclass
class SessionFile:
    """One physical file that belongs to a session."""

    path: Path
    role: str  # "main" | "subagent" | "meta" | "ui" | "api" | "history" | "extra"
    description: str = ""
    # If False, prune must NEVER delete this file even when archived. Use this
    # for files where the conversation is only a small slice of the file (e.g.
    # an IDE-wide SQLite database that contains other state).
    deletable: bool = True

    @property
    def size(self) -> int:
        try:
            return self.path.stat().st_size
        except OSError:
            return 0

    @property
    def mtime(self) -> datetime:
        try:
            return datetime.fromtimestamp(self.path.stat().st_mtime, tz=timezone.utc)
        except OSError:
            return datetime.fromtimestamp(0, tz=timezone.utc)


@dataclass
class SessionRecord:
    """One logical conversation session."""

    tool: str  # tool id, e.g. "cursor", "claude-code"
    session_id: str  # stable id (uuid, timestamp, or hash)
    project: Optional[str] = None  # workspace / project name
    files: list[SessionFile] = field(default_factory=list)
    started_at: Optional[datetime] = None
    last_activity: Optional[datetime] = None
    extra: dict = field(default_factory=dict)

    @property
    def primary_file(self) -> SessionFile:
        for f in self.files:
            if f.role == "main":
                return f
        return self.files[0]

    @property
    def total_size(self) -> int:
        return sum(f.size for f in self.files)

    @property
    def effective_mtime(self) -> datetime:
        """Latest activity timestamp; falls back to file mtime."""
        if self.last_activity is not None:
            return self.last_activity
        if not self.files:
            return datetime.fromtimestamp(0, tz=timezone.utc)
        return max(f.mtime for f in self.files)

    def stable_key(self) -> str:
        """Idempotent identifier across runs."""
        return f"{self.tool}::{self.project or '_'}::{self.session_id}"


class ToolAdapter:
    id: str = ""
    label: str = ""

    def default_roots(self) -> list[Path]:
        raise NotImplementedError

    def discover(self, roots: Optional[list[Path]] = None) -> Iterable[SessionRecord]:
        raise NotImplementedError


def home() -> Path:
    return Path(os.path.expanduser("~"))


def appdata_roaming() -> Optional[Path]:
    """Windows %APPDATA%."""
    val = os.environ.get("APPDATA")
    return Path(val) if val else None


def safe_iterdir(p: Path) -> list[Path]:
    try:
        return list(p.iterdir())
    except (OSError, PermissionError):
        return []
