"""初始化验证：自动检测本机安装的 AI 工具并生成配置文件。

用法:
    python scripts/init.py                    # 检测并生成 config.toml
    python scripts/init.py --dry-run          # 只检测不生成
    python scripts/init.py --output custom.toml  # 指定输出文件
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Optional

# Make sibling tools/ package importable
_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from tools import ALL_ADAPTERS  # noqa: E402


def home() -> Path:
    return Path(os.path.expanduser("~"))


def appdata_roaming() -> Optional[Path]:
    """Windows %APPDATA%."""
    val = os.environ.get("APPDATA")
    return Path(val) if val else None


def detect_tools() -> dict[str, dict]:
    """检测本机安装的 AI 工具及其存储位置。

    返回格式:
    {
        "tool_id": {
            "found": True/False,
            "paths": {"key": "path", ...},
            "label": "Tool Name"
        }
    }
    """
    results = {}

    for adapter_cls in ALL_ADAPTERS:
        adapter = adapter_cls()
        tool_id = adapter.id
        label = adapter.label

        # 获取默认路径
        roots = adapter.default_roots()

        # 检查路径是否存在
        found = any(root.exists() for root in roots)

        # 记录路径信息（使用正斜杠，TOML 兼容）
        paths = {}
        if tool_id == "claude-code":
            paths["claude_projects"] = str(home() / ".claude" / "projects").replace("\\", "/")
        elif tool_id == "claude-globals":
            paths["claude_sessions"] = str(home() / ".claude" / "sessions").replace("\\", "/")
            paths["claude_history"] = str(home() / ".claude" / "history.jsonl").replace("\\", "/")
        elif tool_id == "codex":
            paths["codex_sessions"] = str(home() / ".codex" / "sessions").replace("\\", "/")
        elif tool_id == "cursor":
            paths["cursor_projects"] = str(home() / ".cursor" / "projects").replace("\\", "/")
        elif tool_id == "cursor-chat-sqlite":
            if appdata_roaming():
                paths["cursor_db"] = str(appdata_roaming() / "Cursor" / "User" / "globalStorage" / "state.vscdb").replace("\\", "/")
            else:
                paths["cursor_db"] = str(home() / "Library" / "Application Support" / "Cursor" / "User" / "globalStorage" / "state.vscdb").replace("\\", "/")
        elif tool_id == "cline-vscode":
            if appdata_roaming():
                paths["cline_tasks"] = str(appdata_roaming() / "Code" / "User" / "globalStorage" / "saoudrizwan.claude-dev" / "tasks").replace("\\", "/")
            else:
                paths["cline_tasks"] = str(home() / "Library" / "Application Support" / "Code" / "User" / "globalStorage" / "saoudrizwan.claude-dev" / "tasks").replace("\\", "/")

        results[tool_id] = {
            "found": found,
            "paths": paths,
            "label": label
        }

    return results


def generate_config(detected: dict[str, dict], output_path: Path) -> None:
    """根据检测结果生成配置文件。"""

    lines = [
        "# AI Session Archiver 配置文件",
        "# 由 init.py 自动生成",
        "#",
        "# 检测到的工具已自动配置路径",
        "# 未检测到的工具路径已注释",
        "",
        "[vault]",
        "# 归档输出目录",
        'path = "~/ai-session-archive"',
        "",
    ]

    # 检查是否有任何工具被检测到
    found_any = any(info["found"] for info in detected.values())

    if found_any:
        lines.extend([
            "[paths]",
            "# 各工具的存储路径（自动检测）",
            "",
        ])

        for tool_id, info in detected.items():
            if info["found"] and info["paths"]:
                lines.append(f"# {info['label']} - 已检测到")
                for key, path in info["paths"].items():
                    lines.append(f'{key} = "{path}"')
                lines.append("")
            elif info["paths"]:
                lines.append(f"# {info['label']} - 未检测到")
                for key, path in info["paths"].items():
                    lines.append(f'# {key} = "{path}"')
                lines.append("")

    lines.extend([
        "[archive]",
        "# 归档选项",
        "default_older_than = 15",
        "clean_ide_tags = true",
        'format = "jsonl"',
        "",
        "[prune]",
        "# 清理选项",
        "default_older_than = 15",
        "allow_unarchived = false",
        "",
    ])

    output_path.write_text("\n".join(lines), encoding="utf-8")


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="init",
        description="检测本机 AI 工具并生成配置文件",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="只检测不生成配置文件",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("config.toml"),
        help="输出配置文件路径（默认：config.toml）",
    )

    args = parser.parse_args(argv)

    print("正在检测本机 AI 工具...")
    print()

    detected = detect_tools()

    # 显示检测结果
    found_tools = []
    not_found_tools = []

    for tool_id, info in detected.items():
        if info["found"]:
            found_tools.append(info["label"])
        else:
            not_found_tools.append(info["label"])

    if found_tools:
        print(f"✅ 检测到 {len(found_tools)} 个工具:")
        for label in found_tools:
            print(f"   - {label}")
        print()

    if not_found_tools:
        print(f"❌ 未检测到 {len(not_found_tools)} 个工具:")
        for label in not_found_tools:
            print(f"   - {label}")
        print()

    # 显示路径信息
    print("检测到的存储路径:")
    for tool_id, info in detected.items():
        if info["found"] and info["paths"]:
            print(f"\n{info['label']}:")
            for key, path in info["paths"].items():
                exists = Path(path).exists()
                status = "✓" if exists else "✗"
                print(f"  [{status}] {key}: {path}")

    print()

    # 生成配置文件
    if args.dry_run:
        print("--dry-run 模式，不生成配置文件")
        return 0

    if args.output.exists():
        confirm = input(f"配置文件 {args.output} 已存在，是否覆盖？(y/N): ")
        if confirm.lower() != 'y':
            print("已取消")
            return 0

    generate_config(detected, args.output)
    print(f"✅ 配置文件已生成: {args.output}")
    print()
    print("下一步:")
    print(f"  1. 检查并编辑 {args.output}")
    print(f"  2. 运行扫描: python scripts/archive_sessions.py --config {args.output} scan -v")
    print(f"  3. 归档会话: python scripts/archive_sessions.py --config {args.output} --apply export")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
