# 示例：第一次接触机器，先做 dry-run scan

## 场景

用户问："我在 Cursor 和 Claude Code 都用过 AI，记录到底散落在哪几个目录？体量有多大？"

## 输入

```bash
python .claude/skills/ai-session-archiver/scripts/archive_sessions.py scan -v --limit 15
```

## 实际输出（来自当前 Windows 机器）

```
Discovered 150 sessions across 6 tool(s):

  [claude-code           ]   47 sessions  (    78.8 MB)
  [claude-globals        ]    7 sessions  (     0.0 MB)
  [cline-vscode          ]    6 sessions  (     0.2 MB)
  [codex                 ]   28 sessions  (   482.1 MB)
  [cursor                ]   52 sessions  (     9.9 MB)
  [cursor-chat-sqlite    ]   10 sessions  (  4262.5 MB)

  2026-05-06 09:39  cursor-chat-sqlite     _global                        _globalStorage              4359056.0 KB  (1 files)
  2026-05-06 09:34  claude-code            d--cursor-aries-teach-master   caf4e382-...                   1637.4 KB  (5 files)
  2026-05-06 09:33  claude-code            d--cursor-aries-teach-master   b8fc89f6-...                   1230.5 KB  (5 files)
  2026-05-06 09:33  cursor                 d-cursor-aries-teach-master    2c9e169e-...                      2.7 KB  (1 files)
  2026-05-06 07:14  claude-code            d--cursor-aries-teach-master   d4e1cfdc-...                  4575.1 KB  (11 files)
  ...
```

## 怎么读这份输出

1. **总览行**：每个工具的会话数与原始体量
2. `cursor-chat-sqlite` 的 4.2 GB 是 SQLite DB 文件本身的总大小（IDE 全量状态），归档时**只导出对话相关 keys**，实际归档体积通常 KB 级
3. **明细行**（`-v` 时显示）：按最近活动时间倒排，便于快速看到"最近聊了什么"
4. **multi-files**：例如 claude-code 的某些 session 有 11 个文件 = 1 个主 transcript + 多个 sub-agent transcripts + meta

## 然后呢？

确认体量在预期内后，再决定下一步：

- 想全量归档历史 → `--apply export`（无 `--older-than`）
- 只归档"已经不会再续的旧会话" → `--apply export --older-than 15`
- 只关心 codex 的 → `--tool codex --apply export`

> 这一步**永远不会写入或删除任何文件**，可以放心运行。
