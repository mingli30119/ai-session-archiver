# Changelog

## [0.2.0] - 2026-05-07

### Added

- **配置文件支持**：新增 `--config` 参数，支持通过 TOML 配置文件管理归档路径和默认参数
  - `config.toml` 模板文件，包含 vault 路径、工具路径、归档选项、清理选项
  - 自动加载配置文件中的 `vault.path`、`archive.default_older_than`、`prune.default_older_than` 等参数
  - 命令行参数优先级高于配置文件
- **本地化配置**：预配置了本地路径（`G:/vibe/自媒体/input/AI对话记录`）
- **使用文档**：新增 `examples/using-config-file.md`，详细说明配置文件的使用方法和最佳实践

### Changed

- `--vault` 参数改为可选，可从配置文件读取
- 更新 README.md 和 SKILL.md，添加配置文件使用说明

### Notes

- 需要安装 `tomli` (Python < 3.11) 或使用 Python 3.11+ 的内置 `tomllib`
- 配置文件为可选功能，不影响原有命令行使用方式

## [0.1.0] - 2026-05-06

### Added

- 初始版本，支持 6 个工具的会话扫描、归档与清理：
  - `cursor`（Cursor IDE 项目级 agent transcripts）
  - `cursor-chat-sqlite`（Cursor IDE chat 面板 SQLite 存储）
  - `claude-code`（Claude Code 项目级会话，含 sub-agents）
  - `claude-globals`（Claude Code 全局 session 元数据 + history.jsonl）
  - `codex`（Codex CLI rollouts）
  - `cline-vscode`（Cline VSCode 扩展 tasks）
- 三种命令模式：`scan` / `export` / `prune`，以及组合的 `run`
- 默认 dry-run，需 `--apply` 才会真正写入或删除
- 通过 `manifest.jsonl` 实现幂等导出（重复运行不会重复归档）
- `deletable` 标记保护共享 SQLite 不被误删
- 单 adapter 失败不会阻断整个任务

### Notes

- 归档目录默认 `~/ai-session-archive/`，可用 `--vault` 自定义
- 同一会话由多个文件组成时（如主 transcript + sub-agents + meta）会被合并到单个归档 JSONL
