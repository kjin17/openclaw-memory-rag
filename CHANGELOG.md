# Changelog

Notes are dated by when they were published here, with the measurement dates inside.

## 2026-11-09

Restructured as a technical whitepaper. Scope is now how memory search is used
(structure, configuration, method, measurement procedure) and what it measured.

**Structure**
- New [`docs/whitepaper.md`](docs/whitepaper.md): abstract, background and problem,
  architecture, method, results, limits and refutations, reproduction, change history.
  Korean edition [`docs/whitepaper.ko.md`](docs/whitepaper.ko.md) with the same sections;
  English is canonical.
- `docs/findings.md` merged into the whitepaper; the file now maps the old IDs
  (A1 … I) to sections. `evaluation-method.md` and `ontology-schema.md` become
  Appendices A and B.
- README (English and Korean) shortened to a summary and links.
- Added `AGENTS.md`: what goes in, what stays out, checks before push.
- Added `.gitignore` for Python bytecode (`__pycache__/`, `*.pyc`).

**Removed** (not about retrieval): former findings D3, D4, D5 (D5a kept) and E1–E4 (general operations
notes), and personal anecdotes in the method and schema appendices and tool comments.
No retrieval measurement was removed. The removed operations notes carried their own
figures (D3 four months, D4 25 minutes, E1 eleven days); those are no longer in this
repo. The former README's "recency 6/6" over the first 25 rounds is kept as the
round 17 row in whitepaper §4.1.

**New results** (whitepaper §4.5, §4.8)
- Held-out set weekly values 10-28 … 11-08 (11/13 → 10/13; MRR 0.746 → 0.590). The
  10-28 value was measured on 2026.10.5 and the rest on 2026.10.9, with two
  measuring-tool changes on 11-05, so the 10-28 row is listed but not compared.
- Fixed-baseline regression check: 31/38, run-to-run variation 0 questions, threshold 1;
  five later checks all "same".
- Stale-value probe on 15 changed facts, before and after documentation fixes: first-ranked
  chunk stating an old value 7 → 4; canonical note in top 5 10 → 13. Plus 5 questions
  with an old-value premise.
- In-line correction markers (added 2026-11-07): queries returning an old claim with
  neither a correction nor an indirect counter-example in the top 5, 4 → 0 of 20
  (2026-11-06 → 11-09); the 1 off-topic and 2 indirect-only cases also went to 0.
- Replica re-verified on 2026.10.9: 66/66; decay reads the file's current mtime
  (66/66) rather than the index-stored mtime (61/66).

**Corrections**
- B1's 2026-09-14 rule "check the index's stored timestamp, not the file's" is marked
  build-specific: on 2026.10.9 decay reads the file's current mtime.
- G3's "curated nodes are aged by the index's stored mtime" (published 2026-11-03) is
  marked build-specific for the same reason.
- B1's 2026-09-14 correction gets a dated note (2026-11-11): the eleven notes it
  restored were daily notes, aged by filename date; on the same build, restoring the
  mtime of 14 curated lessons moved the core set 92% → 96% (round 36).
- Age pinning offset: "now minus two days" at introduction, now minus 1.5 days as
  observed in November.

## 2026-11-03

What changed since the previous update (2026-09-24).

**New measurements**
- Rounds 36-1 … 40, from mid-September to late October. Rounds 37 and below ran on
  OpenClaw 2026.9.2, 38 and 39 on 2026.9.7, and 40 on 2026.10.5.
- The 2026.9.7 upgrade starts a new baseline: 44% on the core 25, then 92% after
  round 39 ([findings G1, G4](docs/findings.md)).
- Offline replica of the shipped search path, matching live slot for slot (85/85 on
  9.7, 66/66 on 10.5). It shows hybrid weights, MMR and temporal decay are
  hard-coded ([G2](docs/findings.md)).
- Decay timestamps: dated daily notes use the filename date, the root memo is exempt,
  curated nodes use the indexed mtime ([G3](docs/findings.md)).
- Pre-registered graph test: removing typed predicate lines did not hurt multi-hop
  ([H](docs/findings.md)).
- Index growth from 1,640 to 6,059 chunks; the largest file is down to 4.1%
  ([G5](docs/findings.md)).

**Method**
- Held-out question set, plus retiring questions that were used to steer fixes
  ([evaluation-method §8](docs/evaluation-method.md)).
- Prove an offline replica before you trust it, and re-prove it after every upgrade
  (§9).
- Allocate round numbers once (§10).

**Corrections** (kept in place, marked, and dated; see [findings I](docs/findings.md))
- An earlier internal note said recency weighting has no measurable cost. That is
  refuted: it is forced on from 2026.8.2.
- An earlier internal note said "43 added lessons cost −16 points". Later builds do
  not reproduce it.
- Finding B1's "only `mtime` differed" is narrowed: an `mtime`-only change on an
  indexed file did nothing.
- README: "5 of the 25 questions" is corrected to "5 of the 30".

## 2026-09-24

Harness: pass the agent id explicitly to `memory.search`.

## 2026-09-06

First version: README (English and Korean), method, findings A–F, ontology schema,
`index_census.py`, `evalset_run.py`.
