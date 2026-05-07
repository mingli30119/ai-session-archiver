"""ai-session-archiver — scan, export and prune local AI conversation logs.

Supported tools:
    cursor              ~/.cursor/projects/<id>/agent-transcripts
    cursor-chat-sqlite  %APPDATA%/Cursor/User/{workspaceStorage,globalStorage}/state.vscdb
    claude-code         ~/.claude/projects
    claude-globals      ~/.claude/sessions, ~/.claude/history.jsonl
    codex               ~/.codex/sessions
    cline-vscode        %APPDATA%/Code/User/globalStorage/saoudrizwan.claude-dev/tasks

Usage examples:
    # 1. Plain scan: list every session that would be archived/pruned
    python archive_sessions.py scan

    # 2. Dry-run the full pipeline (DEFAULT). No files are written or deleted.
    python archive_sessions.py run --older-than 15

    # 3. Actually archive everything older than 15 days, then prune originals.
    python archive_sessions.py run --older-than 15 --apply

    # 4. Archive only (no prune)
    python archive_sessions.py export --apply

    # 5. Prune only (originals must already be archived)
    python archive_sessions.py prune --older-than 15 --apply

State / outputs:
    <vault>/manifest.jsonl    one line per archived session (idempotency key)
    <vault>/_state/last_run.json
    <vault>/<tool>/<YYYY-MM>/<project>__<session-id>.jsonl   archived payload
    <vault>/_logs/<run-id>.log
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sys
import textwrap
from collections import defaultdict
from pathlib import Path
from typing import Optional

# Make sibling tools/ package importable both as a script and as a module.
_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from tools import ALL_ADAPTERS, SessionFile, SessionRecord  # noqa: E402
from tools.base import ToolAdapter  # noqa: E402
from tools.cursor_workspace_sqlite import export_db_chat_to_jsonl  # noqa: E402

# Try to import tomllib (Python 3.11+) or fallback to tomli
try:
    import tomllib
except ImportError:
    try:
        import tomli as tomllib
    except ImportError:
        tomllib = None  # type: ignore


DEFAULT_VAULT = Path(os.path.expanduser("~")) / "ai-session-archive"
SAFE_NAME = str.maketrans({c: "_" for c in r'<>:"/\|?*' + chr(0)})


def now_utc() -> dt.datetime:
    return dt.datetime.now(tz=dt.timezone.utc)


def iso(d: dt.datetime) -> str:
    return d.astimezone(dt.timezone.utc).isoformat(timespec="seconds")


def safe(name: str, max_len: int = 80) -> str:
    name = (name or "_").translate(SAFE_NAME).strip(". ")
    if not name:
        name = "_"
    return name[:max_len]


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def parse_jsonl_for_session_meta(path: Path) -> dict:
    """Best-effort metadata sniff from the first/last few JSONL lines.

    Returns: {started_at, last_activity, line_count, sample_keys}
    """
    started: Optional[dt.datetime] = None
    last: Optional[dt.datetime] = None
    line_count = 0
    sample_keys: set[str] = set()
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fp:
            for line in fp:
                line_count += 1
                if line_count <= 3 or line_count % 200 == 0:
                    try:
                        obj = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    if isinstance(obj, dict):
                        sample_keys.update(list(obj.keys())[:8])
                        ts = (
                            obj.get("timestamp")
                            or obj.get("createdAt")
                            or obj.get("created_at")
                            or obj.get("time")
                        )
                        if isinstance(ts, str):
                            try:
                                parsed = dt.datetime.fromisoformat(
                                    ts.replace("Z", "+00:00")
                                )
                                if started is None:
                                    started = parsed
                                last = parsed
                            except ValueError:
                                pass
    except OSError:
        pass
    return {
        "started_at": started,
        "last_activity": last,
        "line_count": line_count,
        "sample_keys": sorted(sample_keys),
    }


def archive_path_for(record: SessionRecord, vault: Path) -> Path:
    yyyymm = record.effective_mtime.strftime("%Y-%m")
    sid = safe(record.session_id)
    if record.project and record.project not in ("_", "_global"):
        fname = f"{safe(record.project)}__{sid}.jsonl"
    else:
        fname = f"{sid}.jsonl"
    return vault / record.tool / yyyymm / fname


def write_archived_jsonl(record: SessionRecord, dest: Path) -> dict:
    """Materialize a session into a single normalized JSONL.

    Layout of the produced JSONL:
        line 1:   {"_archive_meta": {... session info ...}}
        line N+:  one event per line, each tagged with `_file_role` and `_file_name`

    For non-JSONL sources (e.g. JSON arrays), the array is unrolled one element
    per line. For SQLite sources (cursor-chat-sqlite), keys are exported via
    export_db_chat_to_jsonl().
    """
    dest.parent.mkdir(parents=True, exist_ok=True)
    file_stats: list[dict] = []
    total_events = 0

    with open(dest, "w", encoding="utf-8") as out:
        meta = {
            "_archive_meta": {
                "tool": record.tool,
                "session_id": record.session_id,
                "project": record.project,
                "stable_key": record.stable_key(),
                "archived_at": iso(now_utc()),
                "files": [str(f.path) for f in record.files],
                "extra": record.extra,
                "started_at": iso(record.started_at) if record.started_at else None,
                "last_activity": iso(record.last_activity) if record.last_activity else None,
            }
        }
        out.write(json.dumps(meta, ensure_ascii=False) + "\n")
        total_events += 1

        for f in record.files:
            stat = {
                "path": str(f.path),
                "role": f.role,
                "size": f.size,
                "events": 0,
                "format": "unknown",
            }
            file_stats.append(stat)
            if not f.path.exists():
                continue

            if record.tool == "cursor-chat-sqlite" and f.role == "main":
                # Stream SQLite rows into a temporary JSONL then merge in.
                tmp = dest.with_suffix(".sqlite.tmp.jsonl")
                count = export_db_chat_to_jsonl(f.path, tmp)
                stat["format"] = "sqlite-keys"
                stat["events"] = count
                if tmp.exists():
                    with open(tmp, "r", encoding="utf-8") as src:
                        for line in src:
                            out.write(_tag_line(line, f))
                            total_events += 1
                    try:
                        tmp.unlink()
                    except OSError:
                        pass
                continue

            if f.path.suffix.lower() == ".jsonl":
                stat["format"] = "jsonl"
                with open(f.path, "r", encoding="utf-8", errors="replace") as src:
                    for line in src:
                        if not line.strip():
                            continue
                        out.write(_tag_line(line, f))
                        stat["events"] += 1
                        total_events += 1
            elif f.path.suffix.lower() == ".json":
                # Unroll JSON arrays one element per line; otherwise emit as a single line.
                stat["format"] = "json"
                try:
                    payload = json.loads(f.path.read_text(encoding="utf-8", errors="replace"))
                except (json.JSONDecodeError, OSError):
                    payload = {"_archive_warning": f"could not parse {f.path}"}
                if isinstance(payload, list):
                    for item in payload:
                        out.write(
                            _wrap_event(item, f) + "\n"
                        )
                        stat["events"] += 1
                        total_events += 1
                else:
                    out.write(_wrap_event(payload, f) + "\n")
                    stat["events"] += 1
                    total_events += 1
            else:
                stat["format"] = "raw-text"
                try:
                    text = f.path.read_text(encoding="utf-8", errors="replace")
                except OSError:
                    text = ""
                out.write(
                    _wrap_event({"_text_payload": text}, f) + "\n"
                )
                stat["events"] += 1
                total_events += 1
    return {
        "total_events": total_events,
        "files": file_stats,
        "archive_size": dest.stat().st_size,
    }


def _tag_line(line: str, f: SessionFile) -> str:
    """Inject _file_role/_file_name into an already-JSONL line if possible."""
    line = line.rstrip("\r\n")
    try:
        obj = json.loads(line)
        if isinstance(obj, dict):
            obj.setdefault("_file_role", f.role)
            obj.setdefault("_file_name", f.path.name)
            return json.dumps(obj, ensure_ascii=False) + "\n"
    except json.JSONDecodeError:
        pass
    return json.dumps(
        {"_file_role": f.role, "_file_name": f.path.name, "_raw_line": line},
        ensure_ascii=False,
    ) + "\n"


def _wrap_event(payload, f: SessionFile) -> str:
    if isinstance(payload, dict):
        payload = dict(payload)
        payload.setdefault("_file_role", f.role)
        payload.setdefault("_file_name", f.path.name)
        return json.dumps(payload, ensure_ascii=False)
    return json.dumps(
        {"_file_role": f.role, "_file_name": f.path.name, "_payload": payload},
        ensure_ascii=False,
    )


# ----------------------------------------------------------------------------
# Manifest

def load_manifest(vault: Path) -> dict[str, dict]:
    path = vault / "manifest.jsonl"
    out: dict[str, dict] = {}
    if not path.exists():
        return out
    with open(path, "r", encoding="utf-8") as fp:
        for line in fp:
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            key = rec.get("stable_key")
            if key:
                out[key] = rec
    return out


def append_manifest(vault: Path, entry: dict) -> None:
    path = vault / "manifest.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as fp:
        fp.write(json.dumps(entry, ensure_ascii=False) + "\n")


# ----------------------------------------------------------------------------
# Discovery + actions

def discover_all(adapters: list[ToolAdapter]) -> list[SessionRecord]:
    seen: dict[str, SessionRecord] = {}
    for ad in adapters:
        try:
            for rec in ad.discover():
                # If JSONL main file is present, peek it for richer mtime info.
                main = rec.primary_file if rec.files else None
                if main and main.path.suffix.lower() == ".jsonl":
                    info = parse_jsonl_for_session_meta(main.path)
                    if info["started_at"] and rec.started_at is None:
                        rec.started_at = info["started_at"]
                    if info["last_activity"]:
                        rec.last_activity = info["last_activity"]
                    rec.extra.setdefault("sample_keys", info["sample_keys"])
                    rec.extra.setdefault("line_count", info["line_count"])
                seen[rec.stable_key()] = rec
        except Exception as e:  # adapters must never bring the whole run down
            print(f"[warn] adapter {ad.id} failed: {e}", file=sys.stderr)
    return list(seen.values())


def cmd_scan(args: argparse.Namespace) -> int:
    adapters = build_adapters(args.tool)
    records = discover_all(adapters)
    counts: dict[str, list[SessionRecord]] = defaultdict(list)
    for r in records:
        counts[r.tool].append(r)

    print(f"Discovered {len(records)} sessions across {len(counts)} tool(s):\n")
    for tool, recs in sorted(counts.items()):
        size_mb = sum(r.total_size for r in recs) / 1024 / 1024
        print(f"  [{tool:<22}] {len(recs):>4} sessions  ({size_mb:>8.1f} MB)")

    if args.verbose:
        print()
        for rec in sorted(records, key=lambda r: r.effective_mtime, reverse=True)[: args.limit]:
            mtime = rec.effective_mtime.strftime("%Y-%m-%d %H:%M")
            kb = rec.total_size / 1024
            print(
                f"  {mtime}  {rec.tool:<22} {safe(rec.project or '_')[:30]:<30} "
                f"{rec.session_id[:36]:<36}  {kb:>7.1f} KB  ({len(rec.files)} files)"
            )
    return 0


def cmd_export(args: argparse.Namespace) -> int:
    vault = Path(args.vault).expanduser()
    adapters = build_adapters(args.tool)
    records = discover_all(adapters)

    cutoff = compute_cutoff(args.older_than) if args.older_than is not None else None
    if cutoff is not None:
        records = [r for r in records if r.effective_mtime <= cutoff]

    manifest = load_manifest(vault)
    new_entries: list[dict] = []
    skipped = 0
    bytes_archived = 0
    apply = bool(args.apply)
    if not apply:
        print(f"[dry-run] vault: {vault}\n         {len(records)} candidate session(s)")

    for rec in sorted(records, key=lambda r: r.effective_mtime):
        existing = manifest.get(rec.stable_key())
        dest = archive_path_for(rec, vault)
        # Idempotency: same stable_key + same total source size => already archived.
        if existing and existing.get("total_source_size") == rec.total_size and Path(
            existing.get("archive_path", "")
        ).resolve() == dest.resolve():
            skipped += 1
            continue
        if not apply:
            print(f"  [would-archive] {rec.tool:<22} {rec.stable_key()}  -> {dest.relative_to(vault)}")
            continue
        try:
            stats = write_archived_jsonl(rec, dest)
        except OSError as e:
            print(f"  [error] {rec.stable_key()}: {e}", file=sys.stderr)
            continue
        bytes_archived += stats["archive_size"]
        entry = {
            "stable_key": rec.stable_key(),
            "tool": rec.tool,
            "project": rec.project,
            "session_id": rec.session_id,
            "started_at": iso(rec.started_at) if rec.started_at else None,
            "last_activity": iso(rec.last_activity) if rec.last_activity else None,
            "source_paths": [str(f.path) for f in rec.files],
            "archive_path": str(dest),
            "archive_path_rel": str(dest.relative_to(vault)),
            "total_source_size": rec.total_size,
            "stats": stats,
            "archived_at": iso(now_utc()),
        }
        append_manifest(vault, entry)
        new_entries.append(entry)
        print(f"  [archived] {rec.tool:<22} {rec.stable_key()}  ({stats['total_events']} events, {stats['archive_size']/1024:.1f} KB)")

    print()
    print(f"  archived: {len(new_entries)}    skipped (already in manifest): {skipped}")
    if apply:
        print(f"  bytes written: {bytes_archived/1024:.1f} KB    vault: {vault}")
    return 0


def cmd_prune(args: argparse.Namespace) -> int:
    vault = Path(args.vault).expanduser()
    cutoff = compute_cutoff(args.older_than)
    apply = bool(args.apply)
    require_archive = not args.allow_unarchived

    manifest = load_manifest(vault)
    adapters = build_adapters(args.tool)
    records = [r for r in discover_all(adapters) if r.effective_mtime <= cutoff]

    print(
        f"Cutoff: keep activity newer than {cutoff.isoformat(timespec='seconds')} "
        f"(--older-than {args.older_than} day(s))"
    )
    print(f"Candidates older than cutoff: {len(records)}")
    if not apply:
        print("(dry-run; pass --apply to actually delete)")

    deleted_files = 0
    skipped_unarchived = 0
    bytes_deleted = 0
    for rec in records:
        archived = manifest.get(rec.stable_key())
        if require_archive and not archived:
            skipped_unarchived += 1
            print(f"  [skip-not-archived] {rec.stable_key()}")
            continue
        for f in rec.files:
            if not f.path.exists():
                continue
            if not f.deletable:
                continue
            sz = f.size
            if apply:
                try:
                    if rec.tool == "cursor" and f.role == "main":
                        # Also remove the parent <session-uuid> dir for cursor agent
                        # transcripts to keep the tree tidy.
                        parent = f.path.parent
                        f.path.unlink()
                        # remove subagents folder if empty after siblings deleted later
                        deleted_files += 1
                        bytes_deleted += sz
                        # cleanup parent dir if empty (deferred until subagent files
                        # also processed)
                        try:
                            if not any(parent.iterdir()):
                                parent.rmdir()
                        except OSError:
                            pass
                    else:
                        f.path.unlink()
                        deleted_files += 1
                        bytes_deleted += sz
                except OSError as e:
                    print(f"  [error] could not delete {f.path}: {e}", file=sys.stderr)
                    continue
            else:
                deleted_files += 1
                bytes_deleted += sz
        # Try to clean up empty session folders (cursor / claude subagents).
        if apply:
            for f in rec.files:
                try:
                    parent = f.path.parent
                    if parent.exists() and not any(parent.iterdir()):
                        parent.rmdir()
                except OSError:
                    continue

    print()
    print(f"  files {'deleted' if apply else 'would delete'}: {deleted_files}")
    print(f"  bytes {'freed' if apply else 'would free'}: {bytes_deleted/1024:.1f} KB")
    if skipped_unarchived:
        print(
            f"  skipped (no archive yet): {skipped_unarchived}  "
            "(re-run `export --apply` first, or pass --allow-unarchived to force)"
        )
    return 0


def cmd_run(args: argparse.Namespace) -> int:
    """Combined: scan summary -> export -> prune."""
    print("=" * 72)
    print("STEP 1/3  SCAN")
    print("=" * 72)
    cmd_scan(args)
    print("\n" + "=" * 72)
    print("STEP 2/3  EXPORT")
    print("=" * 72)
    rc = cmd_export(args)
    if rc != 0:
        return rc
    print("\n" + "=" * 72)
    print("STEP 3/3  PRUNE")
    print("=" * 72)
    return cmd_prune(args)


# ----------------------------------------------------------------------------

def compute_cutoff(days: int) -> dt.datetime:
    return now_utc() - dt.timedelta(days=days)


def build_adapters(only: Optional[list[str]]) -> list[ToolAdapter]:
    adapters = [cls() for cls in ALL_ADAPTERS]
    if only:
        wanted = set(only)
        adapters = [a for a in adapters if a.id in wanted]
    return adapters


def load_config(config_path: Optional[Path]) -> dict:
    """加载配置文件（TOML 格式）"""
    if not config_path:
        return {}

    if not config_path.exists():
        print(f"[warn] 配置文件不存在: {config_path}", file=sys.stderr)
        return {}

    if tomllib is None:
        print("[warn] 需要安装 tomli 来读取配置文件: pip install tomli", file=sys.stderr)
        return {}

    try:
        with open(config_path, "rb") as f:
            return tomllib.load(f)
    except Exception as e:
        print(f"[error] 读取配置文件失败: {e}", file=sys.stderr)
        return {}


def apply_config(args: argparse.Namespace, config: dict) -> None:
    """将配置文件的值应用到命令行参数"""
    # 应用 vault 路径
    if not args.vault and config.get("vault", {}).get("path"):
        args.vault = config["vault"]["path"]

    # 应用默认 older_than
    if hasattr(args, "older_than"):
        if args.older_than is None:
            if args.cmd == "export":
                args.older_than = config.get("archive", {}).get("default_older_than")
            elif args.cmd in ("prune", "run"):
                args.older_than = config.get("prune", {}).get("default_older_than", 15)

    # 应用 allow_unarchived
    if hasattr(args, "allow_unarchived") and not args.allow_unarchived:
        args.allow_unarchived = config.get("prune", {}).get("allow_unarchived", False)


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="archive_sessions",
        description=textwrap.dedent(__doc__ or "").strip(),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--config",
        type=Path,
        help="配置文件路径（TOML 格式）",
    )
    parser.add_argument(
        "--vault",
        default=None,
        help=f"Archive root (default: {DEFAULT_VAULT} or from config)",
    )
    parser.add_argument(
        "--tool",
        action="append",
        choices=[cls.id for cls in ALL_ADAPTERS],
        help="Limit scan to one or more tool ids (repeatable). Default: all.",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Actually write/delete. Without this flag everything is a dry run.",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_scan = sub.add_parser("scan", help="List discovered sessions; no writes.")
    p_scan.add_argument("-v", "--verbose", action="store_true")
    p_scan.add_argument("--limit", type=int, default=50)
    p_scan.set_defaults(func=cmd_scan)

    p_export = sub.add_parser("export", help="Archive sessions into the vault.")
    p_export.add_argument(
        "--older-than",
        type=int,
        default=None,
        help="Only archive sessions whose last activity is at least N day(s) old.",
    )
    p_export.set_defaults(func=cmd_export)

    p_prune = sub.add_parser("prune", help="Delete originals already in vault and older than --older-than days.")
    p_prune.add_argument("--older-than", type=int, default=15)
    p_prune.add_argument(
        "--allow-unarchived",
        action="store_true",
        help="DANGER: allow deletion of sessions that have not been archived to the vault first.",
    )
    p_prune.set_defaults(func=cmd_prune)

    p_run = sub.add_parser("run", help="scan + export + prune in one go.")
    p_run.add_argument("--older-than", type=int, default=15)
    p_run.add_argument(
        "--allow-unarchived", action="store_true", help="See `prune --allow-unarchived`."
    )
    p_run.add_argument("-v", "--verbose", action="store_true")
    p_run.add_argument("--limit", type=int, default=20)
    p_run.set_defaults(func=cmd_run)

    args = parser.parse_args(argv)

    # 加载配置文件
    config = load_config(args.config) if args.config else {}

    # 应用配置到参数
    apply_config(args, config)

    # 如果 vault 仍然为 None，使用默认值
    if args.vault is None:
        args.vault = str(DEFAULT_VAULT)

    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
