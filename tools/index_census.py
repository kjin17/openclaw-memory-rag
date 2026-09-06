#!/usr/bin/env python3
"""Per-file chunk share for an OpenClaw memory index.

This is the gauge I wish I had had on day one. It answers one question:

    is a single file eating so much of the result window that correct
    answers can no longer fit in it?

Why chunk share and not file size: a bullet-list document splits into many short
chunks and a prose document of the same byte size splits into few. In the incident
that motivated this script, the offending file was getting *smaller* in bytes while
its chunk count grew. Size hid the problem completely.

Usage
    python3 index_census.py                       # default DB path, top 20
    python3 index_census.py --db /path/to.sqlite --top 30 --limit 0.06
    python3 index_census.py --json                # machine-readable

Exit codes
    0  no file above the threshold
    1  at least one file above the threshold
    2  could not read the index

The threshold default (6%) is empirical, from one corpus. Treat it as a starting
point and re-derive it against your own numbers — a gauge that emits a constant you
never checked looks exactly like a measurement.
"""

import argparse
import json
import sqlite3
import sys
from pathlib import Path

DEFAULT_DB = Path.home() / ".openclaw/agents/main/agent/openclaw-agent.sqlite"
DEFAULT_LIMIT = 0.06


def census(db: Path, top: int):
    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    try:
        total, files = con.execute(
            "SELECT COUNT(*), COUNT(DISTINCT path) FROM memory_index_chunks"
        ).fetchone()
        rows = con.execute(
            "SELECT path, COUNT(*) c FROM memory_index_chunks "
            "GROUP BY path ORDER BY c DESC LIMIT ?", (top,)
        ).fetchall()
    finally:
        con.close()
    return total or 0, files or 0, rows


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--db", type=Path, default=DEFAULT_DB)
    ap.add_argument("--top", type=int, default=20)
    ap.add_argument("--limit", type=float, default=DEFAULT_LIMIT,
                    help="alert above this share of total chunks (default 0.06)")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()

    if not a.db.exists():
        print(f"index not found: {a.db}", file=sys.stderr)
        return 2
    try:
        total, files, rows = census(a.db, a.top)
    except sqlite3.Error as e:
        # A missing table usually means "different OpenClaw version", not "broken".
        print(f"could not read index: {e}", file=sys.stderr)
        return 2
    if not total:
        print("index is empty", file=sys.stderr)
        return 2

    over = [(p, c / total, c) for p, c in rows if c / total > a.limit]

    if a.json:
        json.dump({"total": total, "files": files, "limit": a.limit,
                   "top": [{"path": p, "chunks": c, "share": c / total}
                           for p, c in rows],
                   "over": [{"path": p, "share": s, "chunks": c}
                            for p, s, c in over]},
                  sys.stdout, ensure_ascii=False, indent=1)
        print()
        return 1 if over else 0

    print(f"chunks {total} · files {files} · alert above {a.limit * 100:.0f}%")
    for path, c in rows:
        share = c / total
        print(f"{'!!' if share > a.limit else '  '} {share * 100:6.2f}%  {c:5d}  {path}")

    if over:
        p, s, c = over[0]
        print(f"\ntop share {s * 100:.2f}% {p} ({c}/{total}) · over limit: {len(over)}")
        print("one file is crowding the result window — it will push correct answers "
              "out of top-k for neighbouring questions", file=sys.stderr)
        return 1

    print(f"\ntop share {rows[0][1] / total * 100:.2f}% {rows[0][0]} · over limit: 0")
    return 0


if __name__ == "__main__":
    sys.exit(main())
