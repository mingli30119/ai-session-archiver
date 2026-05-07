# 示例：把归档清理设为周期任务

## 思路

每周一次执行：归档新会话 + 清理 15 天前的原件。
每次运行都是幂等的（manifest 已经存在的不会重复处理）。

## Windows：任务计划程序

### 方法 A：通过 PowerShell 注册（一次性命令）

```powershell
$action = New-ScheduledTaskAction -Execute "python.exe" `
    -Argument '"D:\cursor\aries-teach-master\.claude\skills\ai-session-archiver\scripts\archive_sessions.py" --vault "D:\backup\ai-sessions" --apply run --older-than 15' `
    -WorkingDirectory "D:\cursor\aries-teach-master"

$trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Sunday -At 3am

$settings = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -DontStopIfGoingOnBatteries `
    -ExecutionTimeLimit (New-TimeSpan -Hours 1)

Register-ScheduledTask `
    -TaskName "AI-Session-Archiver" `
    -Action $action -Trigger $trigger -Settings $settings `
    -Description "Weekly archive and prune local AI conversation logs"
```

### 方法 B：手动 GUI

1. 打开"任务计划程序"
2. 创建任务 → 名称 `AI-Session-Archiver`
3. 触发器：每周日 3:00
4. 操作：启动程序
   - 程序：`python.exe`
   - 参数：`"D:\cursor\aries-teach-master\.claude\skills\ai-session-archiver\scripts\archive_sessions.py" --vault "D:\backup\ai-sessions" --apply run --older-than 15`
   - 起始位置：`D:\cursor\aries-teach-master`
5. 设置：勾选"如果错过了运行时间则尽快执行"

## macOS：launchd

`~/Library/LaunchAgents/com.local.ai-session-archiver.plist`：

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.local.ai-session-archiver</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/bin/python3</string>
        <string>/path/to/aries-teach-master/.claude/skills/ai-session-archiver/scripts/archive_sessions.py</string>
        <string>--vault</string>
        <string>/Users/me/ai-session-archive</string>
        <string>--apply</string>
        <string>run</string>
        <string>--older-than</string>
        <string>15</string>
    </array>
    <key>StartCalendarInterval</key>
    <dict>
        <key>Weekday</key>
        <integer>0</integer>
        <key>Hour</key>
        <integer>3</integer>
        <key>Minute</key>
        <integer>0</integer>
    </dict>
    <key>StandardOutPath</key>
    <string>/Users/me/ai-session-archive/_logs/cron.out.log</string>
    <key>StandardErrorPath</key>
    <string>/Users/me/ai-session-archive/_logs/cron.err.log</string>
</dict>
</plist>
```

加载：

```bash
launchctl load ~/Library/LaunchAgents/com.local.ai-session-archiver.plist
```

## Linux：cron

```cron
# 每周日 3:00 归档 + 清理 15 天前的原件
0 3 * * 0 /usr/bin/python3 /path/to/.claude/skills/ai-session-archiver/scripts/archive_sessions.py --vault /home/me/ai-session-archive --apply run --older-than 15 >> /home/me/ai-session-archive/_logs/cron.log 2>&1
```

## 验证日程是否生效

下周一早上检查：

1. `~/ai-session-archive/manifest.jsonl` 末尾是否新增了行（看 `archived_at` 字段）
2. `~/ai-session-archive/_logs/cron.*.log`（如果你配了重定向）是否有正常摘要
3. 历史目录中（如 `~/.codex/sessions/2026-02-XX`）已被清空

## 常见问题

- **磁盘满**：把 `--vault` 指向网盘同步目录或外置盘
- **多机器同步**：vault 放到 OneDrive / Dropbox / iCloud Drive 同步目录即可（manifest 是 JSONL，多端拼接后排序去重也成立）
- **调试**：把 `--apply` 拿掉先 dry-run，确认列表正确再加回去
