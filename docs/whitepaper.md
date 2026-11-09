# Measuring and shaping retrieval in an agent's memory

**An OpenClaw case study.** Version 2026-11-09. Change history: [`CHANGELOG.md`](../CHANGELOG.md).
Korean edition: [`whitepaper.ko.md`](whitepaper.ko.md). The English text is canonical.

Appendices: [A. Evaluation method in detail](evaluation-method.md) ·
[B. Ontology schema](ontology-schema.md)

---

## Abstract

We run an [OpenClaw](https://docs.openclaw.ai) agent whose long-term memory is a
Markdown vault indexed by OpenClaw's built-in memory search (local embeddings, SQLite
FTS5, hybrid ranking). To make that memory measurable we wrote a fixed 25-question
evaluation set before tuning anything and re-ran it after every change, one change per
round, for 45 rounds (plus six sub-rounds) between August and November 2026.

The main results:

- **Corpus structure dominated.** Splitting knowledge into one curated note per concept
  moved answer-document recall from 40% to 88% (+48 points) in one round. No retriever
  change came close.
- **Slot occupancy was the dominant variable afterwards.** When one file held 2.03 of
  the top-5 slots per query, recall was 84%; at 1.33 slots it was 92%.
- **The ranking knobs are constants.** An offline replica built from the shipped search
  functions reproduced live results slot for slot on three builds (85/85 slots on
  2026.9.7; 66/66 questions on 2026.10.5 and on 2026.10.9).
  Hybrid weights, MMR and a 30-day temporal decay are hard-coded; on a 17-question
  probe the two always-on stages cost about 3 hits and a third of the MRR.
- **Only curated notes age**, so pinning their age was the largest single lever on
  2026.9.7: 44% → 92% on the core set (five variables moved in that round).
- **The graph's own retrieval effect is not shown.** A pre-registered test found that
  removing the typed links did not hurt multi-hop questions.
- **Since 2026-11-03:** a fixed-baseline regression check (31/38, run-to-run variation
  0 questions); a stale-value probe in which documentation fixes moved the first-ranked
  stale chunk from 7 to 4 of 15 questions; in-line correction markers that took
  "old claim returned without its correction" from 4 to 0 of 20 queries; and a
  replica re-verified on 2026.10.9 that showed decay reads the file's current mtime.

Everything here is n = 1: one corpus, one embedding model, one author of both the
questions and the notes. The directions should transfer; the numbers are ours.

---

## 1. Background and problem

The agent is used daily for operations work. Its memory layer has three parts:

1. an always-injected root memo (a few thousand characters, loaded on every turn),
2. dated daily notes written by the agent,
3. curated notes: one note per component, project, incident or lesson, linked by a
   small set of typed predicates ([Appendix B](ontology-schema.md)).

Everything except the root memo reaches the model only through `memory.search`,
which returns the top-k chunks (k = 5 in our configuration). The practical question
was: **when the agent needs a fact it has written down, does that note come back in
the top 5?** Before August 2026 we had no way to answer it, and every tuning claim
was anecdotal.

Two properties of the problem shaped the method:

- Retrieval is a shared window. Any change that lifts one document can push another
  out for an unrelated query, so a change can only be judged on the whole set.
- The ranking code changes with agent upgrades, and the corpus changes daily. Numbers
  are only comparable within one build and one measurement path.

---

## 2. System architecture

```
question
   │
   ├─ vector search   local llama.cpp server · embeddinggemma-300m (768-dim)
   └─ text search     SQLite FTS5 (unicode61), with a keyword fallback scorer
   │
   ├─ hybrid blend 0.7 / 0.3  →  temporal decay (30-day half-life)  →  MMR (λ 0.7)
   │      ↑ all three hard-coded in every build measured (through 2026.10.9)
   ▼
top-k chunks → agent context
```

| layer | choice | reason |
|---|---|---|
| Embeddings | local `llama.cpp` managed server | no API key, no expiry, works offline; ~95 MB resident |
| Index | SQLite (FTS5 + vector table) alongside the agent DB | one file to back up; snapshot-able |
| Chunking | 400 tokens / 80 overlap | product default; file *shape* mattered more than chunk size |
| Corpus | Markdown vault indexed by a path allowlist | plain files, diffable, editable by a person |
| Ontology | typed links between notes, at most 8 predicates | [Appendix B](ontology-schema.md) |

**Ranking pipeline (read from the shipped code, verified by replica, §3.6).** Even at
k = 5 the ranker draws 200 vector and 200 keyword candidates, blends them 0.7 / 0.3,
applies temporal decay, runs MMR, then cuts to k. None of these parameters has a
configuration field. For Korean sentence queries the FTS5 path (all terms ANDed)
usually returns nothing and a fallback keyword scorer runs; on our 17-question probe
a median of 169 of 200 keyword candidates saturated at the maximum score, so ordering
was effectively decided by vector similarity.

**Decay timestamp sources.** Dated daily notes are aged by the date in their filename;
the root memo and undated files in the memory folder are exempt; all other files,
which in practice means the curated notes, are aged by modification time (on
2026.10.9, the file's current mtime at query time; see §4.5).

**Corpus composition.** In September 2026 about 56% of chunks were curated notes,
39% generated material and 5% the root memo, in 1,640 chunks / 285 files. By early
November the index held 6,059 chunks / 1,092 files; the split was not re-measured.

---

## 3. Method

Full detail, including what went wrong, is in [Appendix A](evaluation-method.md).

### 3.1 Evaluation set

Written before any tuning. Each question records the document(s) that must appear in
the top-k for the answer to be reachable. Scoring is mechanical: the expected document
is in the top 5 or it is not. Answer prose is not graded.

| kind | n | what it catches |
|---|---|---|
| `fact` | 8 | a stated value can be found at all |
| `multihop` | 9 | two documents that must be combined |
| `causal` | 8 | the reason, which usually lives in a different note than the symptom |
| `negative` | 5 | what confidently answers a question that has no good answer |
| `recency` | 6 | recent events; prices the recency weighting (reported separately) |

The headline number is the auto-scored 25 (`fact` + `multihop` + `causal`). `recency`
and `negative` are reported beside it, never folded in. From round 42 a semi-automatic
`negative` judgement runs at the retrieval layer (does any top-5 chunk contain all the
premise terms); it is not a hallucination measure.

Larger occupancy probes (17 and 54 questions, the latter with 49 auto-scored) were
added in late September and read at k = 5, 6 and 20 to see how far outside the window
a miss sits.

### 3.2 One change per round, re-run everything, log outside the index

Each round changes one thing and re-runs every question. Every round is logged,
including the ones that lost points. Round records are kept **outside the indexed
corpus**, because a results log inside it grew to 41 chunks and displaced correct
answers (§4.7).

### 3.3 Held-out set and retired questions

By late October most of the core 25 had been the target of at least one fix, so they
are now a regression check, not evidence that a change helped. Questions are sorted
into *used* (steered a fix), *near-ceiling*, and *held out*. The held-out set
(`holdout_v1`) has 15 questions, 13 auto-scored, stored outside the index, pinned by a
content hash and loaded by the harness through an import. A held-out question that is
looked at while fixing something moves to *used* and is replaced. With n = 13 only a
difference of two or more questions counts as signal, and the held-out set is measured
weekly rather than after every change.

### 3.4 Fixed-baseline regression check (added 2026-11-08)

The round runner compared each round with the previous healthy round, which lets a
regression leak in one question at a time without ever tripping a threshold. The
regression check compares against a **fixed baseline** instead:

- Score = core 25 + held-out 13 = 38 points; `recency` and `negative` are side metrics.
- The baseline is measured twice in a row. Threshold = max(1, score difference between
  the two runs, number of questions whose result differed). Questions that flip
  between the two runs are marked flaky and excluded from "new misses".
- Verdict: **regression** if the score drops by 2 or more, or 2 or more stable
  questions newly miss (exit code 2). One new stable miss is a warning.
- A health gate runs first: if more than 5% of the 51 queries return nothing, error or
  time out, no score is produced (exit code 3).

It measures only the retrieval layer. A behavioural regression caused by changing an
instruction's wording is out of scope.

### 3.5 Stale-value probe (added 2026-11-07)

The core set asks "is the right document in the top 5". It cannot see a different
failure: the right document is retrieved, but the chunk that comes back (or a chunk
ranked above it) states a value that is no longer true. The probe:

- 15 facts whose value is known to have changed (software versions, configuration
  values, scheduler constants, device settings). Questions are written without the
  value words and frozen before searching.
- The current value of each fact is read from the live system, not from a file.
- Each of the 75 top-5 chunks is read in full by a person and labelled *old value*,
  *current value*, *before→after* (both in one chunk), or *unrelated*. Values in
  proposals or hypotheticals are not counted.
- Reported: which labels appear in the top 5, the label of the first-ranked chunk, the
  label of the first chunk that carries any value, and whether the canonical note
  ranks in the top 5 and carries the current value.
- A second variant asks 5 questions that embed the old value as a premise.

The 15 facts were chosen because they changed, so the counts are case counts, not a
staleness rate for the corpus.

### 3.6 Offline replica harness

Because the ranking constants are not configurable, most "what if" questions can only
be answered offline: copy the index read-only, import the shipped search functions,
replay queries, and change one stage at a time. A replica is trusted only after:

1. it matches live top-k **in order** on every question, re-checked after every
   upgrade, and
2. deliberate breakages (drop the query prefix, shift the decay clock, turn MMR off)
   make the match collapse.

### 3.7 Harness hazards we control for

- **Measurement path.** A CLI path that took a lock added ~52 s stalls to some queries;
  the service API took ~1 s for the same query. The path is stamped into every result
  file and latency is never compared across paths.
- **Round numbering.** Round numbers are allocated when a round runs. Six rounds
  recorded late were inserted as sub-rounds 36-1 … 36-6 in time order.
- **Count what changed between rounds** (`find -newer` against the previous result
  file) before attributing a score change.

---

## 4. Results

Numbers from different OpenClaw builds are not compared. Builds: rounds ≤ 24 on
2026.8.2, 25–37 on 2026.9.2, 38–39 on 2026.9.7, 40 on 2026.10.5, 41 onwards on
2026.10.9. Rounds 42 and 43 changed the measuring tool and start new comparison points.

### 4.1 Score history (selected rounds)

| round | date | change | core 25 | notes |
|---|---|---|---|---|
| 1 | 08-22 | curated ontology vs. flat notes | 40% → **88%** | +48 points (§4.2) |
| 2 | 08-30 | re-measure after 8 days | 56% | generated material reached 82% of chunks |
| 6 | 08-30 | reverse dependency edges written into notes | 92% | |
| 20 | 09-06 | strengthened a component note | **96%** | multihop 9/9 |
| 21–23 | 09-06 | edit → shrink → revert one file | 92% | target unfixed; an unrelated `fact` broke |
| 24 | 09-06 | restored that file's original mtime | 96% | content byte-identical (see B1 correction) |
| 36-1 | 09-14 | back-filled 11 days of generated digests | 80% | §4.7, D5a |
| 36-4…6 | 09-15 | graph ablation | 84% / 96% / 84% | §4.6 |
| 37 | 09-30 | merged six heading-only chunks in the root memo | 68% | 2026.9.2 drift; see G1 |
| 38 | 10-03 | **2026.9.7 baseline** | **44%** | 49-question set 24/49, recency 1/6 |
| 39 | 10-03 | five changes incl. age pinning of curated notes | **92%** | 49-question set 43/49; no question dropped |
| 42 | 11-05 | measuring tool changed (health gate, `negative` auto) | 92% (23/25) | new comparison point |
| 44 | 11-07 | documentation clean-up of stale values | 88% (22/25) | new misses #13 #18 #24, not attributed |
| 45 | 11-08 | regression-check baseline | 84% (21/25) | 31/38 with held-out (§4.8) |

### 4.2 Corpus structure

**A1. One curated note per concept: +48 points.** Before: a flat set of dated notes
plus one large always-loaded memo. After: typed nodes (components, projects,
incidents, lessons) with the raw notes still present. The largest effect measured.
(§4.6 narrows what produced it.)

**A2. Slot occupancy is the dominant variable.** Count how many of the top-5 results
come from the same file.

```
one file averaging 2.03 of 5 slots   →  84%
the same file reduced to 1.33 slots  →  92%
```

Corpus size barely moved between the two measurements.

**A3. Count chunks, not files or bytes.** Bullet-list documents split into many short
chunks; prose of the same byte size splits into few. A crowding file can shrink in
bytes while its chunk count grows. A per-file chunk-share gauge is in §6; we alert
above 6% for a single file (an empirical threshold). The largest file peaked at 8.4%
in late September and was 4.1% in early November.

**A4. Derivatives outrank their sources.** Generated material that quotes source notes
reached 82% of the index at its worst, 32% of it one generator's working log. Moving
it out of the index (archive, not delete) is the fix.

**A5. Heading-only chunks.** The root memo had six chunks containing only a section
heading. Merging each heading into its first item, character count unchanged, cut the
memo's share of result slots from 25.2% to 21.5% and recovered one question.

### 4.3 Recency weighting

**B1. Touching a file can be a ranking action.** A/B with byte-identical content:
file re-saved today 92%, original mtime 96%. The question that broke was not about
that file.

> **Correction (2026-09-14).** "Only `mtime` differed" overstates what this A/B
> isolated. A week later, restoring the `mtime` of eleven already-indexed notes moved
> no question. On that build the index is driven by content hashes; the round-24
> restore coincided with a content revert that triggered a re-index. Revised rule
> then: check the timestamp the index used, not the file's.
>
> **Note (2026-11-04).** On 2026.10.9 the replica matches live only when decay reads
> the file's current mtime at query time (66/66), not the index-stored mtime (61/66).
> On that build an `mtime`-only change does move ranking. The rule is therefore
> build-specific: verify which timestamp your build reads (§4.5).

**B2. A recency boost can beat a better match on every component.** We observed a
document that scored higher on both vector and text similarity and still lost on the
final score, because the decay was applied after blending.

**G3. Only curated notes age.** Daily notes use their filename date and the root memo
is exempt, so the decay landed almost entirely on curated nodes, the notes curated
most carefully.

**G4. Pinning the age of curated nodes.** With no setting available, a daily job sets
the `mtime` of curated nodes to a fixed short age (now minus two days when introduced;
now minus 1.5 days as observed in November); the real edit date lives
in each note's frontmatter. Round 39 extended it from lessons to component, project and
schema notes together with four other changes: 44% → **92%** (23/25) on the core set,
24/49 → **43/49** on the larger set, no question dropping and 19 rising.

- Five variables moved in that round. The replica decomposition attributes most of
  the gain to age pinning; the other four were not cut apart.
- It contradicts B1's "restore the honest timestamp" rule. We accept that for curated,
  evergreen notes because the decay is a constant; we would not do it to dated notes.
- A pinned age is not neutral: as it drifts from 2 to 3 days during the day, lessons
  lose 4.5–6.7% of their score, larger on our probe than the typical gap between
  neighbouring top-5 results (~0.04).

**G1. A score can decay by the clock alone.** On a 49-question set the score went from
28/49 to 24/49 within days with nothing changed, because curated notes aged.

### 4.4 Interventions that did not work

| intervention | effect |
|---|---|
| remove the crowding file (C1) | 0 points; vacated slots went to the next-freshest file |
| remove an unrelated large file (C2) | −4 points |
| **strengthen the note that should have won** (C3) | +4 points, and again +4 in a later round |

Strengthening means putting the answer in the note that ought to own it, using the
vocabulary the question uses.

### 4.5 Ranking constants and replica verification (G2)

The replica imports the shipped search functions and replays queries against a
read-only copy of the index.

| build | replica vs. live (top-k, in order) | deliberate breakages |
|---|---|---|
| 2026.9.7 | 85/85 slots | — |
| 2026.10.5 | 66/66 questions | query prefix removed 1/66 · decay clock +30 days 6/66 · MMR off 1/66 |
| 2026.10.9 (11-04) | 66/66 chunk order, path order and top-1 | prefix removed 2/66 · index-stored mtime instead of file mtime 61/66 |

2026.10.5 added a task prefix to the query embedding input (`task: search result |
query: `); without it the replica matched 1/66. On 2026.10.9 the hard-coded constants
were unchanged (hybrid 0.7 / 0.3, candidate multiplier ×4, MMR λ 0.7, 30-day decay,
candidate cap max(200, k)). The 10.9 MT=index comparison rests on a result file whose
raw output was not retained; the MT=stat 66/66 output is retained.

Flipping the constants in the replica on 17 questions (2026.9.7):

| variant | hits / 17 | MRR |
|---|---|---|
| live (hybrid + decay + MMR) | 13 | 0.50 |
| hybrid + decay | 15 | 0.56 |
| hybrid + MMR | 13 | 0.66 |
| hybrid only | 16 | 0.76 |

On our corpus the two always-on stages cost about three hits in seventeen and a third
of the MRR. n = 17; read it as a direction.

### 4.6 Does the graph itself help retrieval? Not shown (H)

Committed before measuring: **if typed links help retrieval, removing them should hurt
`multihop`.**

| arm | change | core 25 | multihop |
|---|---|---|---|
| A | as is | 84% | 9/9 |
| B | remove predicate lines and generated backlink blocks (6.75% of corpus) | 96% | 9/9 |
| C | remove only the generated backlink blocks (3.85%) | 84% | 8/9 |

`multihop` did not move, so by the pre-registered rule the graph's retrieval
contribution is not shown. B's +12 was unexpected; arm C rules out "less volume, so
things reshuffled". The remaining guess (repetitive predicate lines blur what
distinguishes notes) was weakened when deleting 316 boilerplate predicate lines in the
replica changed nothing. Our reading of A1: what moved retrieval was the split into
one well-named note per concept. The typed links remain useful as an audit structure
for people.

### 4.7 Measurement hazards observed

- **D1. The measurement log contaminates its own measurement.** A results log inside
  the indexed vault grew to 41 chunks and displaced correct answers. Keep it outside.
  The same shape reappeared in November: a result file that quoted old claims verbatim
  took a top-5 slot in 9 of 20 queries of the next measurement (§4.8).
- **D2. "Not in top 5" is not "not in the corpus."** Widening k reorders results;
  check k before diagnosing a broken index.
- **D5a. Count what changed between rounds before naming a cause.** A 16-point drop
  (96% → 80%) after back-filling generated digests was first blamed on the digests.
  A control round that removed only the digests recovered half; the other half came
  from 22 unrelated notes edited between the rounds.
- **D6. Confident-and-wrong is invisible to recall.** Removing generated artifacts did
  not change accuracy, but the top hit for a `negative` question moved from a generated
  artifact (score 0.696, wrong) to the relevant note (0.433).

### 4.8 Results since 2026-11-03

**Held-out set, weekly (`holdout_v1`, same content hash throughout).**

| date | measuring tool | held-out hits / 13 | MRR |
|---|---|---|---|
| 10-28 | baseline | 11 | 0.746 |
| 11-04 | unchanged | 11 | 0.669 |
| 11-05 | round 42 (tool changed) | 10 | 0.615 |
| 11-05 | round 43 (age fields stored, tool changed) | 10 | 0.692 |
| 11-08 | round 45 (regression baseline) | 10 | 0.590 |

The 11-04 change (same hits, two questions from rank 1 to rank 2) was below the
two-question threshold and was not attributed. From 11-05 the comparison point is the
new tool.

**Regression check (§3.4).** Baseline 2026-11-08: **31/38** (core 21/25, held-out
10/13, MRR 0.590), `recency` 5/6, `negative` auto 4/5 (1 ambiguous), health gate 0/51.
Two consecutive runs differed on 0 questions, including the full top-5 lists, so
retrieval itself is deterministic and the threshold is the floor value 1. Same-day
movement of ±1 that we saw earlier came from the live corpus changing between runs,
not from the engine. Five checks taken before and after documentation changes on 11-08
and 11-09 all returned "same": 31/38 on 11-08, 32/38 on 11-09 (one core question newly
hit), 0 new misses. The regression path itself was tested by injecting two misses into a fake
search (verdict "regression", 31 → 29, exit code 2).

**Stale-value probe (§3.5), before and after documentation fixes.** Between the two
runs, three kinds of fix were applied: version tables were labelled with their
measurement date and the command that reads the current value; node notes without a
value got a one-line read command; long component notes got a 3–5 line "current
values" block at the top. Other notes also changed in between, so not all movement is
attributable to these fixes.

| 15 facts | 11-07 | 11-09 |
|---|---|---|
| top 5 has only old values | 4 | 2 |
| top 5 has both old and current | 8 | 9 |
| top 5 has only current | 2 | 3 |
| top 5 has no value | 1 | 1 |
| **first-ranked chunk states an old value** | **7** | **4** |
| first chunk carrying a value states an old value | 9 | 6 |
| canonical note in top 5 | 10 | 13 |
| canonical chunk lets you read the current value | 4 | 6 |

The current values were re-read from the live systems on 11-09 and were unchanged.
Under the core set's scoring rule the 11-07 run would have scored 10/15, yet only 4 of
those 10 canonical chunks carried the current value. Remaining holes were structural:
a date label that sits outside the table's chunk, a "current values" block ranked
7th, and a value present only in a history line.

With old values embedded in the question as a premise (5 questions, 11-09), every
question had a correcting chunk somewhere in the top 5, but the first-ranked chunk was
current in only 1 of 5, and the canonical note was in the top 5 in 2 of 5. Premise
words pull old-value chunks up.

**In-line correction markers.** Lessons that had been refuted carried their correction
as a separate line at the end. Measured with 20 natural-language queries
(2026-11-06): in 4 queries an old-claim chunk came back with no correction anywhere in
the top 5, plus 1 more on an off-topic query. Each of the three lessons that carried only
an appended refutation line showed up uncorrected; the two whose opening claim had been
rewritten never did. After adding a short correction marker inside the same line as the
old claim (2026-11-09, same 20 queries): 0 such queries. All 9 queries that still
returned an old-claim chunk now had the marker inside that chunk. Rank did not drop
(e.g. top-1 0.762 → 0.780): the marker does not reduce exposure, it makes the
correction travel with the claim. The same 20 queries against two other agents'
indexes, which do not include the root memo, gave 0 uncorrected cases as well.

---

## 5. Limits and refutations

### 5.1 Limits

- **n = 1.** One corpus, one person, one embedding model.
- **Blind spot.** Every expected document is a curated note. An intervention that
  loses knowledge held only in raw daily notes scores as harmless.
- **Unscored questions.** The 5 `negative` questions of the 30 were not scored through
  round 41; from round 42 a retrieval-layer proxy runs. Answer-layer hallucination is
  not measured.
- **The core 25 have been taught to.** Effects are judged on the held-out set.
- **Retrieval, not answers.** The stale-value and correction-marker probes measure what
  is retrieved. The answering model may still filter stale chunks by their date labels;
  the tool returns ~700-character snippets, and in some cases the current value sat
  outside the snippet.
- **Hand-picked probes.** The stale-value facts and the correction-marker queries were
  chosen by us; read them as case counts.
- **Upgrades change the ranking code.** Each upgrade starts a new baseline.
- **Untested branches.** On 2026.10.9 the importance and project-key ranking branches
  had no data in our index (0 of 6,214 rows) and were not exercised by the replica.

### 5.2 Corrections log

Earlier claims are kept, marked, and dated.

| date | earlier claim | now |
|---|---|---|
| 2026-08-30 → 2026-09-03 | recency weighting has no measurable cost | refuted: only true where it could be disabled; forced on from 2026.8.2 (§4.5) |
| 2026-08-30 → 2026-09-03 | "43 added lessons cost −16 points" | not reproduced on later builds; isolating 32 lessons made the score worse, adding nine more did not lower it |
| 2026-09-06 → 2026-09-14 | B1 isolates `mtime` alone | overstated: an `mtime`-only change on an indexed file did nothing on that build |
| 2026-09-06 → 2026-10-07 | recency is "not disableable in this build" | broader: none of the hybrid/MMR/decay parameters are configurable (§4.5) |
| 2026-08-22 → 2026-09-15 | the ontology's +48 is the graph | the curated split is shown; the graph's retrieval effect is not (§4.6) |
| 2026-09-14 → 2026-11-04 | "check the index's stored timestamp, not the file's" (B1), and "curated nodes are aged by the index's stored mtime" (G3, published 2026-11-03) | build-specific: on 2026.10.9 decay reads the file's current mtime (66/66 vs 61/66) |
| README, 2026-11-03 | "5 of the 25 questions have never been scored" | "5 of the 30" |

---

## 6. Reproduction

### 6.1 Tools in this repository

- [`tools/index_census.py`](../tools/index_census.py): total chunks, file count and
  per-file chunk share for an OpenClaw memory index; exits 1 when one file exceeds a
  share threshold (default 6%).

  ```
  python3 tools/index_census.py --top 20 --limit 0.06
  ```

- [`tools/evalset_run.py`](../tools/evalset_run.py): the round runner. Replace
  `QUESTIONS` with your own; it calls `memory.search` through the gateway, captures
  stderr, stamps the measurement path, and writes one JSON file per round.

  ```
  python3 tools/evalset_run.py 1
  ```

The gauge in SQL, if you prefer:

```sql
SELECT path, COUNT(*) c,
       ROUND(100.0*COUNT(*)/(SELECT COUNT(*) FROM memory_index_chunks),2) pct
FROM memory_index_chunks GROUP BY path ORDER BY c DESC LIMIT 20;
```

### 6.2 Procedures described but not shipped

The regression check, the stale-value probe and the replica harness depend on our
folder layout and on hashed module names inside the installed OpenClaw build, so they
are described rather than shipped. To build your own replica:

1. Copy the index with SQLite's backup API from a read-only connection; never open the
   live file for writing.
2. Locate the shipped search module in the installed `dist/` by its exports (the file
   names are content-hashed and change with every release), and the port of the local
   embedding server.
3. Replay a fixed question list against live `memory.search` and against the replica;
   require identical top-k order on every question.
4. Break it deliberately (query prefix, decay clock, MMR) and confirm the match
   collapses. Re-run steps 2–4 after every upgrade.

### 6.3 What we would do from day one

1. Write the evaluation set first; 25 questions is enough.
2. Add the per-file chunk-share gauge.
3. Prefer one well-named note per concept over long index documents.
4. Keep generated material and measurement records out of the index.
5. Change one thing per round and re-run everything.
6. Take a fresh baseline after every upgrade; read the shipped ranking code.
7. Retire questions used to steer a fix; keep a held-out set and a fixed regression
   baseline.
8. Put correction markers inside the line they correct, and date-label value tables
   inside the same chunk as the values.

---

## 7. Change history

See [`CHANGELOG.md`](../CHANGELOG.md). Earlier finding identifiers (A1, B1, G2, H …)
are kept in this document so older links and citations still resolve.

---

MIT licensed. Contradicting measurements are especially welcome.
