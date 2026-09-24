#!/usr/bin/env python3
"""A retrieval evaluation harness small enough to actually keep running.

One round = ask every question, record which documents came back, score whether the
expected document was in the top-k. Nothing about answer prose is graded — grading
prose turns a repeatable measurement into an opinion.

    python3 evalset_run.py 26          # label this round "26"

Replace QUESTIONS with your own before using this. The ones below are shaped like
mine but are placeholders; a question is only useful if you know which document
*must* be retrieved for it to be answerable.

Design decisions that came from being burned, not from taste:

  · Three numbers per round, not one — hit rate, context size, latency.
    A change that halves your context but drops accuracy is a loss. Watching a
    single number guarantees you will eventually congratulate yourself for one.

  · `negative` questions are NOT auto-scored. "Does it invent a relationship that
    doesn't exist" cannot be decided from rank order. Print the top-k and read it.
    The automatic proxy (top-1 score) is a hint, not a verdict.

  · `recency` questions are scored but reported SEPARATELY, because the main set
    has to stay comparable with round 1. Never quietly widen the denominator of a
    number you are tracking over time.

  · stderr is captured. In one round, 10 of 36 queries stalled for ~52 seconds and
    the reason was printed on stderr the whole time ("timed out waiting for lock").
    A runner that captures only success output cannot see a side-path failure: the
    main result still arrives, the exit code is still 0, and nothing looks wrong.

  · The measurement path is stamped into the output file. Latency measured through
    a CLI that takes a lock is not comparable with latency measured through the
    running service — in my case 52s vs 1.8s for the identical query. If you switch
    paths and don't record it, you will compare incomparable rounds forever.

  · Output files are per-round and never overwritten. The trend is the point.
"""

import json
import statistics
import subprocess
import sys
import time
from pathlib import Path

MAX_RESULTS = 5
OUT_DIR = Path.home() / ".openclaw/state/evalset"
SEARCH_PATH = "gateway"      # stamped into the output; change if you change the call

# (kind, question, [path fragments — a hit on any one scores the question])
#
# kinds: fact | multihop | causal | negative | recency
#   fact      a stated value lives in exactly one node
#   multihop  the answer needs two nodes combined
#   causal    the reason lives in a different node than the symptom
#   negative  there is NO good answer; you are watching what answers confidently
#   recency   about something recent; prices the recency weighting in your ranker
QUESTIONS = [
    ("fact", "When does the nightly cleanup job run?", ["components/cleanup-job"]),
    ("fact", "How many predicates does the note schema allow?", ["ontology/schema"]),
    ("multihop", "Which scheduled jobs depend on the API whose quota is limited?",
     ["components/quota-api", "components/scheduler"]),
    ("causal", "Why did the watchdog stay silent for three days?",
     ["incidents/2026-01-14", "components/watchdog"]),
    ("negative", "Which model does the billing service use?", []),   # no such thing
    ("recency", "What changed in the deployment process most recently?",
     ["projects/deployment"]),
]


def search(query: str):
    """Return (hits, elapsed_ms, note). `note` carries the first stderr line."""
    t0 = time.time()
    r = subprocess.run(
        ["openclaw", "gateway", "call", "memory.search",
         "--params", json.dumps({"query": query, "maxResults": MAX_RESULTS, "agentId": "main"}),
         "--json", "--timeout", "30000"],
        capture_output=True, text=True, timeout=180)
    ms = (time.time() - t0) * 1000

    try:
        hits = json.loads(r.stdout).get("results", [])
    except Exception:
        hits = []

    note = r.stderr.strip().splitlines()[0][:160] if r.stderr.strip() else ""
    if not hits and not note:
        # Separate "nothing matched" from "the question never reached the engine".
        # A silent zero is a place this runner was fooled once.
        try:
            note = (json.loads(r.stdout or "{}").get("error") or {}).get("message", "")[:160]
        except Exception:
            note = "empty response"
        note = note or "empty response"
    return hits, ms, note


def path_of(hit) -> str:
    return hit.get("path") or hit.get("source") or ""


def main() -> int:
    label = sys.argv[1] if len(sys.argv) > 1 else "unlabeled"
    rows, per_kind = [], {}

    for kind, question, expect in QUESTIONS:
        hits, ms, note = search(question)
        paths = [path_of(h) for h in hits]
        context_chars = sum(len(h.get("snippet") or "") for h in hits)

        if kind == "negative":
            score = None          # judged by a human, deliberately
        else:
            score = any(e in p for e in expect for p in paths)

        rows.append({"kind": kind, "q": question, "expect": expect,
                     "hits": paths, "score": score,
                     "ms": round(ms), "chars": context_chars, "note": note})
        b = per_kind.setdefault(kind, {"n": 0, "ok": 0})
        b["n"] += 1
        b["ok"] += 1 if score else 0

    print(f"=== {label} ===")
    core_n = core_ok = 0
    for kind in ("fact", "multihop", "causal", "negative", "recency"):
        b = per_kind.get(kind)
        if not b:
            continue
        if kind == "negative":
            print(f"{kind:9s} judged by hand ({b['n']} questions)")
        else:
            print(f"{kind:9s} {b['ok']}/{b['n']}")
        if kind in ("fact", "multihop", "causal"):
            core_n, core_ok = core_n + b["n"], core_ok + b["ok"]

    if core_n:
        print(f"core total {core_ok}/{core_n} ({core_ok / core_n * 100:.1f}%)"
              "   ← the number to track; recency and negative stay out of it")

    lat = [r["ms"] for r in rows]
    if lat:
        print(f"latency median {statistics.median(lat):.0f} ms · max {max(lat):.0f} ms"
              f"   (path: {SEARCH_PATH} — do not compare across paths)")

    stalls = [r for r in rows if r["note"]]
    if stalls:
        print(f"\n{len(stalls)} question(s) carried a stderr note — read these:")
        for r in stalls[:5]:
            print(f"  · {r['q'][:50]} → {r['note']}")

    failed = [r for r in rows if r["score"] is False]
    if failed:
        print("\n-- misses")
        for r in failed:
            print(f"  [{r['kind']}] {r['q']}")
            for e in r["expect"]:
                print(f"      expected → {e}")
            for p in r["hits"][:5]:
                print(f"      got      → {p}")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUT_DIR / f"{label}.json"
    out.write_text(json.dumps(
        {"label": label, "path": SEARCH_PATH, "k": MAX_RESULTS, "rows": rows,
         "per_kind": per_kind}, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\nsaved {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
