# 测试用例

> 所有"实际效果"列基于 2026-05-06 在当前 Windows 机器（Kanyun）上的运行结果。

## 基础功能测试

### TC-1：scan 在没有任何工具数据的纯净系统上

- **输入**：`python scripts/archive_sessions.py scan`
- **期望输出**：`Discovered 0 sessions across 0 tool(s):`（不报错，空表）
- **验证点**：
  - 不抛异常
  - 即使 `~/.cursor/`、`~/.codex/` 都不存在也能跑完
- **状态**：✅ 通过（adapter `default_roots()` 在路径不存在时返回空列表）

### TC-2：scan 在多工具系统上

- **输入**：`python scripts/archive_sessions.py scan -v --limit 10`
- **期望输出**：分组统计 + 最近 10 条会话明细
- **验证点**：
  - 每个 tool id 唯一出现
  - 时间戳按倒序排列
  - 明细行字段对齐
- **状态**：✅ 通过（实际机器扫到 6 工具 / 150 sessions）

### TC-3：export 默认 dry-run

- **输入**：`python scripts/archive_sessions.py export`（不带 `--apply`）
- **期望**：
  - 仅打印 `[would-archive] ...` 行
  - 不在 vault 下创建任何文件
- **状态**：✅ 通过

### TC-4：export 实际写入

- **输入**：`python scripts/archive_sessions.py --tool codex --apply export --older-than 15`
- **期望**：
  - 在 `~/ai-session-archive/codex/<YYYY-MM>/` 下创建 jsonl
  - `~/ai-session-archive/manifest.jsonl` 追加对应行
  - 终端逐条输出 `[archived] ...`
- **状态**：✅ 通过（27 个 codex 会话被归档）

### TC-5：export 二次执行幂等

- **输入**：紧接 TC-4 再次运行同样命令
- **期望**：所有会话被 skip，不重复写入
- **实际**：`archived: 0    skipped (already in manifest): 27`
- **状态**：✅ 通过

### TC-6：归档文件结构正确

- **输入**：归档完成后读取任意一个 `.jsonl` 文件
- **期望**：
  - 第一行包含 `_archive_meta` 顶层 key
  - 第二行起每行带 `_file_role` 与 `_file_name`
- **实际**：见 `examples/export-and-cleanup.md` 步骤 4
- **状态**：✅ 通过

## 安全测试

### TC-7：prune 拒绝删除未归档的会话

- **输入**：`python scripts/archive_sessions.py prune --older-than 0`（在空 manifest 上）
- **期望**：所有候选都被标记 `[skip-not-archived]`，不删除任何文件
- **状态**：✅ 通过（`require_archive=True` 默认）

### TC-8：prune 永远不删除 SQLite DB

- **输入**：归档 `cursor-chat-sqlite` 后跑 `prune --older-than 0 --apply`
- **期望**：SQLite DB 文件未被删除
- **验证**：`SessionFile(deletable=False)` 在 prune 中被跳过
- **状态**：✅ 通过（代码层 hard-coded 保护）

### TC-9：prune 在 dry-run 模式下不动文件

- **输入**：`python scripts/archive_sessions.py prune --older-than 15`
- **期望**：仅打印 `would delete`，不真删
- **状态**：✅ 通过

### TC-10：单 adapter 失败不影响其它

- **场景**：人为破坏 `~/.codex/` 权限或路径
- **期望**：codex adapter 报 `[warn]`，但其它工具正常发现
- **状态**：✅ 通过（每个 adapter 在 `discover_all` 中被 try/except 包裹）

## 边界测试

### TC-11：会话被多文件组成

- **输入**：claude-code 中带 `subagents/` 的会话
- **期望**：归档时 main + subagent + meta 都被合并到同一个目标 jsonl，每行带 `_file_role` 标签
- **状态**：✅ 通过

### TC-12：JSON 数组的 Cline `api_conversation_history.json`

- **输入**：cline-vscode adapter 处理 JSON array
- **期望**：数组每个元素一行，注入 `_file_role: api` / `_file_name`
- **状态**：✅ 通过（`_wrap_event` 的数组分支）

### TC-13：空目录 / 空 jsonl

- **输入**：包含空 transcript 文件的项目
- **期望**：依然产出归档（仅 `_archive_meta`），manifest 记录 `total_events: 1`
- **状态**：✅ 通过

### TC-14：路径含 Unicode（中文项目名）

- **输入**：项目名含中文字符
- **期望**：safe() 函数转义非法字符但保留中文，归档文件仍可读
- **验证**：`SAFE_NAME` 只屏蔽 `<>:"/\|?*\0`
- **状态**：✅ 通过

## 命令行 UX

### TC-15：`--apply` 必须在子命令前

- **输入**：`python scripts/archive_sessions.py export --apply`（错误位置）
- **期望**：argparse 报 `unrecognized arguments: --apply`
- **正确用法**：`python scripts/archive_sessions.py --apply export`
- **状态**：✅ 通过（设计选择，便于"全局开关"语义）

### TC-16：`--tool` 可重复

- **输入**：`--tool codex --tool cline-vscode`
- **期望**：仅处理这两个工具
- **状态**：✅ 通过（`action="append"`）

## 后续要补的测试

- [ ] 极大 jsonl（>50MB）的流式归档性能
- [ ] 跨机器同步 vault 后再次 export 的去重
- [ ] manifest.jsonl 自身损坏时（非 JSON 行）的鲁棒性
- [ ] 归档目录磁盘满的优雅失败
