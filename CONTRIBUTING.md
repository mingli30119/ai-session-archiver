# 贡献指南

感谢你对 AI Session Archiver 的关注！我们欢迎各种形式的贡献。

## 如何贡献

### 报告 Bug

如果你发现了 bug，请创建一个 Issue，包含：
- 问题描述
- 复现步骤
- 预期行为 vs 实际行为
- 环境信息（操作系统、Python 版本、工具版本）
- 相关日志或截图

### 提出功能建议

如果你有功能建议，请创建一个 Issue，包含：
- 功能描述
- 使用场景
- 为什么需要这个功能
- 可能的实现方案（可选）

### 添加新工具支持

这是最受欢迎的贡献类型！如果你想添加对新 AI 工具的支持，请按照以下步骤：

## Adapter 开发指南

### 1. 了解工具的存储结构

首先，你需要找到工具的对话记录存储位置和格式：

**常见位置：**
- Windows: `%APPDATA%/ToolName/` 或 `%LOCALAPPDATA%/ToolName/`
- macOS: `~/Library/Application Support/ToolName/`
- Linux: `~/.config/ToolName/` 或 `~/.local/share/ToolName/`

**常见格式：**
- JSON / JSONL 文件
- SQLite 数据库
- 纯文本日志

### 2. 创建 Adapter 类

在 `scripts/tools/` 目录下创建新文件，例如 `mytool.py`：

```python
"""MyTool AI assistant.

Layout:
    ~/.mytool/sessions/<session-id>.jsonl
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterable, Optional

from .base import SessionFile, SessionRecord, ToolAdapter, home


class MyToolAdapter(ToolAdapter):
    id = "mytool"  # 唯一标识符
    label = "MyTool AI Assistant"  # 显示名称

    def default_roots(self) -> list[Path]:
        """返回默认的存储根目录列表。"""
        root = home() / ".mytool" / "sessions"
        return [root] if root.exists() else []

    def discover(
        self, roots: Optional[list[Path]] = None
    ) -> Iterable[SessionRecord]:
        """扫描并返回所有会话记录。"""
        roots = roots or self.default_roots()
        for root in roots:
            if not root.exists():
                continue
            
            # 遍历会话文件
            for session_file in root.glob("*.jsonl"):
                session_id = session_file.stem
                
                yield SessionRecord(
                    tool=self.id,
                    session_id=session_id,
                    project=None,  # 如果有项目信息，填入这里
                    files=[
                        SessionFile(
                            session_file,
                            role="main",
                            description="mytool session"
                        )
                    ],
                )
```

### 3. 注册 Adapter

在 `scripts/tools/__init__.py` 中添加你的 adapter：

```python
from .mytool import MyToolAdapter

ALL_ADAPTERS = [
    # ... 现有的 adapters
    MyToolAdapter,
]
```

### 4. 测试

```bash
# 测试扫描
python scripts/archive_sessions.py --tool mytool scan -v

# 测试归档
python scripts/archive_sessions.py --tool mytool export --dry-run

# 实际归档
python scripts/archive_sessions.py --tool mytool --apply export
```

### 5. 更新文档

- 在 README.md 的"支持的工具"表格中添加你的工具
- 在 `scripts/init.py` 中添加路径检测逻辑
- 更新 CHANGELOG.md

### 6. 提交 Pull Request

- Fork 本仓库
- 创建新分支：`git checkout -b add-mytool-support`
- 提交更改：`git commit -m "Add MyTool support"`
- 推送分支：`git push origin add-mytool-support`
- 创建 Pull Request

## Adapter 开发注意事项

### SessionFile 的 role 字段

- `"main"`: 主会话文件
- `"subagent"`: 子 agent 会话
- `"meta"`: 元数据文件
- `"ui"`: UI 相关数据
- `"api"`: API 调用记录
- `"history"`: 历史记录

### deletable 标记

如果文件是共享的（如 SQLite 数据库包含其他数据），设置 `deletable=False`：

```python
SessionFile(
    db_path,
    role="ui",
    deletable=False,  # 不允许 prune 删除
    description="shared database"
)
```

### 错误处理

使用 `safe_iterdir()` 避免权限错误：

```python
from .base import safe_iterdir

for child in safe_iterdir(parent_dir):
    # ...
```

### 时间戳解析

如果文件名或内容包含时间戳，尽量解析并填入 `started_at` 和 `last_activity`：

```python
from datetime import datetime, timezone

rec = SessionRecord(
    tool=self.id,
    session_id=session_id,
    started_at=datetime.fromisoformat(timestamp_str).replace(tzinfo=timezone.utc),
    last_activity=datetime.fromtimestamp(file.stat().st_mtime, tz=timezone.utc),
    files=[...],
)
```

## 代码规范

- 使用 Python 3.8+ 语法
- 遵循 PEP 8 代码风格
- 添加类型注解（`from __future__ import annotations`）
- 添加 docstring 说明存储布局
- 使用 `Path` 而不是字符串路径

## 测试清单

在提交 PR 前，请确保：

- [ ] `scan` 命令能正确发现会话
- [ ] `export` 命令能正确归档会话
- [ ] `prune` 命令不会误删共享文件
- [ ] 在 Windows / macOS / Linux 上测试（如果可能）
- [ ] 更新了 README.md
- [ ] 更新了 CHANGELOG.md
- [ ] 添加了示例配置到 `config.example.toml`

## 需要帮助？

如果你在开发过程中遇到问题，欢迎：
- 创建 Issue 提问
- 查看现有 adapter 的实现作为参考
- 在 PR 中标注 "WIP"（Work In Progress）寻求反馈

## 行为准则

- 尊重他人
- 保持友好和专业
- 接受建设性批评
- 关注对项目最有利的事情

感谢你的贡献！🎉
