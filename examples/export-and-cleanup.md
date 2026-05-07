# 示例：完整归档 + 15 天后清理

## 场景

用户希望：
- 把所有 AI 对话备份到 `D:\backup\ai-sessions\`
- 但本地仍保留最近 15 天的对话不动
- 超过 15 天的原文件清掉，节省磁盘

## 步骤 1：先归档全部历史（不限时间，幂等）

```powershell
python .claude/skills/ai-session-archiver/scripts/archive_sessions.py `
    --vault "D:\backup\ai-sessions" --apply export
```

输出（节选）：

```
  [archived] codex                  codex::_::019c3258-f41e-7ed2-b974-8802618f8e80  (14 events, 43.2 KB)
  [archived] codex                  codex::_::019cdb06-b5b7-7750-8b87-4ba5332cae02  (10 events, 55.8 KB)
  [archived] claude-code            claude-code::d--cursor-aries-teach-master::caf4e382-...  (1284 events, 1.6 MB)
  ...

  archived: 150    skipped (already in manifest): 0
  bytes written: 565423.7 KB    vault: D:\backup\ai-sessions
```

## 步骤 2：先 dry-run 看看 prune 会删什么

```powershell
python .claude/skills/ai-session-archiver/scripts/archive_sessions.py `
    --vault "D:\backup\ai-sessions" prune --older-than 15
```

输出：

```
Cutoff: keep activity newer than 2026-04-21T09:45:24+00:00 (--older-than 15 day(s))
Candidates older than cutoff: 27
(dry-run; pass --apply to actually delete)

  files would delete: 27
  bytes would free: 493665.3 KB
```

确认删除清单是预期的（这里 27 个 codex 文件、约 482 MB）。

## 步骤 3：实际清理

```powershell
python .claude/skills/ai-session-archiver/scripts/archive_sessions.py `
    --vault "D:\backup\ai-sessions" --apply prune --older-than 15
```

执行完后：
- `~/.codex/sessions/2026/02/...` 下 15 天前的 jsonl 已被删除
- 空目录会被自动清理
- `D:\backup\ai-sessions\codex\2026-02\...jsonl` 仍完整保留（含归档元信息）

## 步骤 4：验证可还原性

抽一个归档文件检查：

```powershell
Get-Content "D:\backup\ai-sessions\codex\2026-02\019c3258-...jsonl" -TotalCount 1
# 第一行：{"_archive_meta":{"tool":"codex","session_id":"019c3258-...",...,"files":["C:\\Users\\Kanyun\\.codex\\sessions\\2026\\02\\06\\rollout-...jsonl"]}}
```

第一行的 `_archive_meta.files` 列出原始路径，第二行起是完整事件流（含 user input、model thinking、tool calls、tool results、最终输出）。需要还原时，按原路径写回去即可。

## 一次跑完三步（推荐）

```powershell
python .claude/skills/ai-session-archiver/scripts/archive_sessions.py `
    --vault "D:\backup\ai-sessions" --apply run --older-than 15
```

`run` = `scan -v`（前 20 条）→ `export`（含 `--older-than` 过滤）→ `prune`，一气呵成。
