# Changelog

Notes are dated by when they were published here, with the measurement dates inside.

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
