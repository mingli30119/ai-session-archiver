# AI Session Archiver

> 跨工具扫描、统一归档、定期清理本地 AI 对话记录

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)

## 为什么需要这个工具？

如果你使用多个 AI 编程助手（Claude Code、Cursor、Codex、GitHub Copilot 等），你的对话记录会分散在不同的目录下，持续膨胀，占用大量磁盘空间。这些对话记录是宝贵的知识资产——包含决策过程、调试思路、验证过的方案——但缺乏统一的管理方式。

**AI Session Archiver** 让你能够：
- 📦 **统一归档**：将所有工具的对话记录导出为标准 JSONL 格式
- 🔍 **跨工具扫描**：自动发现本机安装的 AI 工具及其存储位置
- 🧹 **安全清理**：删除已归档的旧对话，释放磁盘空间
- 🔒 **幂等执行**：重复运行不会重复归档，支持定期任务
- 🛡️ **安全优先**：默认 dry-run，保护性删除，不会误删重要文件

## 支持的工具

| 工具 | 状态 | 存储位置 |
|------|------|---------|
| **Claude Code** | ✅ 完整支持 | `~/.claude/projects` |
| **Codex CLI** | ✅ 完整支持 | `~/.codex/sessions` |
| **Cursor IDE** | ✅ 完整支持 | `~/.cursor/projects` + SQLite |
| **Cline (VSCode)** | ✅ 完整支持 | `%APPDATA%/Code/.../saoudrizwan.claude-dev/tasks` |
| **GitHub Copilot** | 🔜 计划中 | 待调研 |
| **OpenCode** | 🔜 计划中 | 待调研 |
| **OpenClaw** | 🔜 计划中 | 待调研 |
| 其他工具 | 💡 欢迎贡献 | 见 [CONTRIBUTING.md](CONTRIBUTING.md) |

## 快速开始

### 1. 安装依赖

```bash
# Python 3.11+ 无需额外依赖
# Python 3.10 及以下需要安装 tomli
pip install tomli
```

### 2. 初始化配置（推荐）

运行初始化脚本，自动检测本机 AI 工具并生成配置文件：

```bash
python scripts/init.py
```

输出示例：
```
正在检测本机 AI 工具...

✅ 检测到 4 个工具:
   - Claude Code (~/.claude/projects)
   - Codex CLI (~/.codex/sessions)
   - Cursor IDE (per-project agent transcripts)
   - Cline VSCode

检测到的存储路径:
Claude Code (~/.claude/projects):
  [✓] claude_projects: C:/Users/YOUR_USERNAME/.claude/projects

✅ 配置文件已生成: config.toml
```

### 3. 扫描会话

查看本机有多少 AI 对话记录：

```bash
python scripts/archive_sessions.py --config config.toml scan -v
```

输出示例：
```
Discovered 150 sessions across 4 tool(s):
  [claude-code           ]   47 sessions  (    78.8 MB)
  [codex                 ]   28 sessions  (   482.1 MB)
  [cursor                ]   52 sessions  (     9.9 MB)
  [cline-vscode          ]   23 sessions  (     5.5 MB)
```

### 4. 归档会话

```bash
# 先 dry-run 看看会归档什么
python scripts/archive_sessions.py --config config.toml export

# 实际归档
python scripts/archive_sessions.py --config config.toml --apply export
```

### 5. 清理旧会话

```bash
# 删除 15 天前的原件（已归档的）
python scripts/archive_sessions.py --config config.toml --apply prune --older-than 15
```

### 6. 一键完成全流程

```bash
# 扫描 + 归档 + 清理
python scripts/archive_sessions.py --config config.toml --apply run --older-than 15
```

## 核心特性

### 🔍 自动检测

初始化脚本会自动检测本机安装的 AI 工具，无需手动配置路径。

### 🔒 安全机制

- **默认 dry-run**：不加 `--apply` 永远不会写入或删除文件
- **幂等性保证**：通过 `manifest.jsonl` 避免重复归档
- **保护性删除**：只删除已归档的会话，SQLite 等共享文件永不删除
- **错误隔离**：单个工具失败不影响其他工具

### 📦 归档格式

每个会话归档为单个 JSONL 文件：

```jsonl
{"_archive_meta": {"tool": "claude-code", "session_id": "...", "started_at": "...", ...}}
{"timestamp": "...", "type": "user", "content": [...], "_file_role": "main"}
{"timestamp": "...", "type": "assistant", "content": [...], "_file_role": "main"}
```

- 首行：会话元信息
- 后续行：事件流（用户输入、模型输出、工具调用等）
- 每行标注来源文件（`_file_role`、`_file_name`）

### 🔄 定期任务

配合系统任务计划程序，实现自动归档和清理：

**Windows 任务计划程序：**
```batch
python scripts/archive_sessions.py --config config.toml --apply run --older-than 15
```

**macOS/Linux cron：**
```cron
0 3 * * 0 cd /path/to/ai-session-archiver && python scripts/archive_sessions.py --config config.toml --apply run --older-than 15
```

## 命令速查

| 场景 | 命令 |
|------|------|
| 初始化配置 | `python scripts/init.py` |
| 扫描会话 | `python scripts/archive_sessions.py --config config.toml scan -v` |
| 归档会话 | `python scripts/archive_sessions.py --config config.toml --apply export` |
| 清理旧会话 | `python scripts/archive_sessions.py --config config.toml --apply prune` |
| 一键完成 | `python scripts/archive_sessions.py --config config.toml --apply run` |
| 只处理某个工具 | `python scripts/archive_sessions.py --tool claude-code --apply export` |
| 自定义归档路径 | `python scripts/archive_sessions.py --vault ~/backup --apply export` |

## 归档目录结构

```
~/ai-session-archive/
├── manifest.jsonl                    # 归档索引（幂等键）
├── claude-code/
│   └── 2026-04/
│       └── project-name__session-id.jsonl
├── codex/
│   └── 2026-02/
│       └── session-id.jsonl
├── cursor/
│   └── 2026-04/
│       └── project-name__session-id.jsonl
└── cline-vscode/
    └── 2026-02/
        └── timestamp.jsonl
```

## 文档

- [使用配置文件](examples/using-config-file.md) - 详细的配置文件使用指南
- [定期任务配置](examples/periodic-task.md) - Windows/macOS/Linux 定期任务设置
- [贡献指南](CONTRIBUTING.md) - 如何添加新工具支持
- [CHANGELOG](CHANGELOG.md) - 版本变更记录

## 贡献

欢迎贡献新工具的支持！查看 [CONTRIBUTING.md](CONTRIBUTING.md) 了解如何：
- 添加新工具的 adapter
- 提交 bug 报告
- 提出功能建议

## 常见问题

### Q: 归档后原始文件会被删除吗？

A: 不会。`export` 命令只归档，不删除。只有 `prune` 命令会删除已归档的原始文件，且必须加 `--apply` 才会实际执行。

### Q: 如何恢复已删除的会话？

A: 归档文件保存在 vault 目录中，可以手动查看或导入。但原始文件一旦删除无法恢复，建议先备份 vault 目录。

### Q: 支持云端会话吗（如 ChatGPT 网页版）？

A: 不支持。本工具只处理本地存储的会话记录。云端会话需要从浏览器或官方 API 导出。

### Q: 如何添加新工具支持？

A: 查看 [CONTRIBUTING.md](CONTRIBUTING.md) 中的 Adapter 开发指南。

## 许可证

[MIT License](LICENSE)

## 致谢

感谢所有 AI 编程工具的开发者，让编程变得更高效。

---

**如果这个工具对你有帮助，请给个 ⭐️ Star！**
