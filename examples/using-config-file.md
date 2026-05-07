# 使用配置文件的完整示例

本文档展示如何使用配置文件来管理 ai-session-archiver。

## 前置准备

### 1. 安装依赖

```bash
# Python 3.11+ 自带 tomllib，无需安装
# Python 3.10 及以下需要安装 tomli
pip install tomli
```

### 2. 创建配置文件

在项目根目录创建 `config.toml`：

```toml
[vault]
# 归档输出目录
path = "G:/vibe/自媒体/input/AI对话记录"

[paths]
# 各工具的存储路径（可选，不配置则使用默认路径）
claude_projects = "C:/Users/YOUR_USERNAME/.claude/projects"
claude_sessions = "C:/Users/YOUR_USERNAME/.claude/sessions"
claude_history = "C:/Users/YOUR_USERNAME/.claude/history.jsonl"
codex_sessions = "C:/Users/YOUR_USERNAME/.codex/sessions"
cursor_projects = "C:/Users/YOUR_USERNAME/.cursor/projects"
cursor_db = "C:/Users/YOUR_USERNAME/AppData/Roaming/Cursor/User/globalStorage/state.vscdb"
cline_tasks = "C:/Users/YOUR_USERNAME/AppData/Roaming/Code/User/globalStorage/saoudrizwan.claude-dev/tasks"

[archive]
# 归档选项
default_older_than = 15  # 默认归档 15 天前的会话
clean_ide_tags = true    # 清理 IDE 标签噪音（未来功能）
format = "jsonl"         # 归档格式

[prune]
# 清理选项
default_older_than = 15      # 默认删除 15 天前的原件
allow_unarchived = false     # 禁止删除未归档的会话
```

## 使用场景

### 场景 1：首次使用 - 扫描现有会话

```bash
# 扫描所有工具的会话
python scripts/archive_sessions.py --config config.toml scan -v

# 只扫描前 30 个会话
python scripts/archive_sessions.py --config config.toml scan -v --limit 30

# 只扫描 Claude Code
python scripts/archive_sessions.py --config config.toml --tool claude-code scan -v
```

**输出示例：**
```
Discovered 150 sessions across 6 tool(s):
  [claude-code           ]   47 sessions  (    78.8 MB)
  [codex                 ]   28 sessions  (   482.1 MB)
  [cursor                ]   52 sessions  (     9.9 MB)
  ...
```

### 场景 2：归档历史会话

```bash
# 归档所有会话（dry-run，不会实际写入）
python scripts/archive_sessions.py --config config.toml export

# 实际归档所有会话
python scripts/archive_sessions.py --config config.toml --apply export

# 只归档 30 天前的会话
python scripts/archive_sessions.py --config config.toml --apply export --older-than 30
```

**输出示例：**
```
Exporting sessions to G:/vibe/自媒体/input/AI对话记录
  [claude-code] 47 sessions
  [codex] 28 sessions
  ...
Exported: 75 sessions (560.7 MB)
Skipped (already archived): 0
```

### 场景 3：清理旧会话

```bash
# 查看会删除什么（dry-run）
python scripts/archive_sessions.py --config config.toml prune

# 实际删除 15 天前的原件（配置文件中的默认值）
python scripts/archive_sessions.py --config config.toml --apply prune

# 删除 30 天前的原件
python scripts/archive_sessions.py --config config.toml --apply prune --older-than 30
```

**安全机制：**
- 只删除已归档的会话
- SQLite 数据库等共享文件不会被删除
- 默认 dry-run，必须加 `--apply` 才会实际删除

### 场景 4：一键完成全流程

```bash
# 扫描 + 归档 + 清理（dry-run）
python scripts/archive_sessions.py --config config.toml run

# 实际执行全流程
python scripts/archive_sessions.py --config config.toml --apply run

# 自定义保留天数
python scripts/archive_sessions.py --config config.toml --apply run --older-than 30
```

**输出示例：**
```
========================================================================
STEP 1/3  SCAN
========================================================================
Discovered 150 sessions across 6 tool(s):
  ...

========================================================================
STEP 2/3  EXPORT
========================================================================
Exported: 75 sessions (560.7 MB)

========================================================================
STEP 3/3  PRUNE
========================================================================
Deleted: 75 files (560.7 MB freed)
```

## 配置文件 vs 命令行参数

### 优先级

命令行参数 > 配置文件 > 默认值

```bash
# 配置文件中 vault.path = "G:/vibe/..."
# 但命令行指定了 --vault，则使用命令行的值
python scripts/archive_sessions.py --config config.toml --vault D:/backup/ai scan
```

### 何时使用配置文件

**推荐使用配置文件：**
- 固定的归档路径
- 固定的保留天数策略
- 需要定期执行（配合任务计划程序）
- 多人协作，统一配置

**推荐使用命令行参数：**
- 临时修改归档路径
- 一次性操作
- 测试不同的参数组合

## 定期任务配置

### Windows 任务计划程序

创建批处理文件 `archive_ai_sessions.bat`：

```batch
@echo off
cd /d G:\vibe\my-skills\ai-session-archiver
python scripts\archive_sessions.py --config config.toml --apply run --older-than 15 >> logs\archive.log 2>&1
```

在任务计划程序中：
1. 创建基本任务
2. 触发器：每周日凌晨 3:00
3. 操作：启动程序 `G:\vibe\my-skills\ai-session-archiver\archive_ai_sessions.bat`

### macOS / Linux (cron)

编辑 crontab：

```bash
crontab -e
```

添加：

```cron
# 每周日凌晨 3:00 归档和清理 AI 会话
0 3 * * 0 cd /path/to/ai-session-archiver && python scripts/archive_sessions.py --config config.toml --apply run --older-than 15 >> logs/archive.log 2>&1
```

## 归档目录结构

使用配置文件后，归档目录结构：

```
G:/vibe/自媒体/input/AI对话记录/
├── manifest.jsonl                    # 归档索引（幂等键）
├── _logs/                            # 执行日志（未来功能）
├── codex/
│   ├── 2026-02/
│   │   └── 019c3258-...jsonl
│   └── 2026-03/
├── claude-code/
│   └── 2026-04/
│       └── g--vibe__5f61fb24-...jsonl
├── cursor/
│   └── 2026-04/
│       └── d-cursor-aries-teach-master__08d14a74-...jsonl
└── ...
```

## 常见问题

### Q: 配置文件放在哪里？

A: 建议放在项目根目录（`ai-session-archiver/config.toml`），也可以放在任意位置，使用时指定完整路径：

```bash
python scripts/archive_sessions.py --config /path/to/my-config.toml scan
```

### Q: 如何验证配置文件是否生效？

A: 使用 `scan` 命令查看归档路径：

```bash
python scripts/archive_sessions.py --config config.toml scan -v
```

输出会显示 vault 路径。

### Q: 配置文件中的路径可以使用 `~` 吗？

A: 可以，但建议使用绝对路径以避免歧义：

```toml
# 推荐
path = "G:/vibe/自媒体/input/AI对话记录"

# 也可以（会展开为用户主目录）
path = "~/ai-session-archive"
```

### Q: 如何只归档某个工具的会话？

A: 使用 `--tool` 参数：

```bash
python scripts/archive_sessions.py --config config.toml --tool claude-code --apply export
```

### Q: 配置文件中的 `paths` 部分是必需的吗？

A: 不是必需的。如果不配置，会使用默认路径（`~/.claude`、`~/.codex` 等）。只有当你的路径不是默认位置时才需要配置。

## 最佳实践

1. **首次使用先 scan**：了解会归档多少数据
2. **使用配置文件**：避免每次输入长路径
3. **定期执行**：配合任务计划程序，每周自动归档和清理
4. **保留近期会话**：使用 `--older-than 15` 保留最近 15 天的会话在 IDE 中
5. **验证归档**：归档后检查 `manifest.jsonl`，确保会话已记录
6. **备份归档目录**：定期备份 vault 目录到外置硬盘或云盘

## 下一步

- 查看 [README.md](../README.md) 了解更多命令
- 查看 [SKILL.md](../SKILL.md) 了解工作流程
- 查看 [examples/](../examples/) 了解更多使用场景
