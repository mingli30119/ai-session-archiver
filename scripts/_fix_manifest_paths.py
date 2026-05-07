"""One-off helper: fix archive_path in a manifest after the vault has moved.

Usage:
    python _fix_manifest_paths.py <manifest.jsonl> <old_root> <new_root>
"""

from __future__ import annotations

import json
import sys
from pathlib import Path


def main(argv: list[str]) -> int:
    if len(argv) != 4:
        print(__doc__)
        return 2
    mf = Path(argv[1])
    old_root = argv[2]
    new_root = argv[3]
    rows = []
    with open(mf, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            ap = obj.get("archive_path", "")
            if ap.startswith(old_root) and not ap.startswith(new_root):
                obj["archive_path"] = ap.replace(old_root, new_root, 1)
            rows.append(obj)
    with open(mf, "w", encoding="utf-8") as f:
        for obj in rows:
            f.write(json.dumps(obj, ensure_ascii=False) + "\n")
    print(f"patched {len(rows)} manifest entries -> {mf}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
