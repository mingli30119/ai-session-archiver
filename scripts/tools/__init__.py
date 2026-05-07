"""Per-tool session adapters.

Every adapter must implement:
    - id: str (short tool key)
    - default_roots() -> list[Path]
    - discover(roots: list[Path]) -> Iterable[SessionRecord]

A SessionRecord describes ONE conversation session, possibly composed of
multiple files (main transcript + sub-agent transcripts + metadata).
"""

from .base import SessionRecord, SessionFile, ToolAdapter
from .cursor_agent import CursorAgentAdapter
from .cursor_workspace_sqlite import CursorWorkspaceSqliteAdapter
from .claude_code import ClaudeCodeAdapter
from .claude_globals import ClaudeGlobalsAdapter
from .codex_cli import CodexCliAdapter
from .cline_vscode import ClineVscodeAdapter

ALL_ADAPTERS: list[type[ToolAdapter]] = [
    CursorAgentAdapter,
    CursorWorkspaceSqliteAdapter,
    ClaudeCodeAdapter,
    ClaudeGlobalsAdapter,
    CodexCliAdapter,
    ClineVscodeAdapter,
]

__all__ = [
    "SessionRecord",
    "SessionFile",
    "ToolAdapter",
    "ALL_ADAPTERS",
    "CursorAgentAdapter",
    "CursorWorkspaceSqliteAdapter",
    "ClaudeCodeAdapter",
    "ClaudeGlobalsAdapter",
    "CodexCliAdapter",
    "ClineVscodeAdapter",
]
