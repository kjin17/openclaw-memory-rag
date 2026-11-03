# Findings

Every number here came from a round of the evaluation set described in
[`evaluation-method.md`](evaluation-method.md). Where a finding was later
contradicted, the contradiction is kept and marked — those are the useful ones.

---

## A. Corpus structure

### A1. Introducing a linked ontology: +48 points

The single largest effect I measured, in one round. Before: a flat pile of dated
notes plus one large always-loaded memo. After: typed nodes (components, projects,
incidents, lessons) linked to a schema note, with the raw notes still present.

Nothing I did to the retriever afterwards produced a comparable move. If you are
choosing where to spend a week, spend it here.

### A2. The dominant variable is slot occupancy, not corpus size

For each query, count how many of the top-5 results come from the *same* file.

```
one file averaging 2.03 of 5 slots   →  84%
the same file reduced to 1.33 slots  →  92%
```

Corpus size barely moved between those two measurements. **Diversity of the result
window is the thing.** A retriever that returns five chunks of the same document has
effectively returned one result.

### A3. Count chunks, not files, and never bytes

Bullet-list documents split into many short chunks; prose of the same byte size
splits into few. In the incident that started this, the offending file was getting
*smaller* in bytes while its chunk count grew. Both "number of files" and "file size"
hid the problem completely.

Gauge it directly:

```sql
SELECT path, COUNT(*) c,
       ROUND(100.0*COUNT(*)/(SELECT COUNT(*) FROM memory_index_chunks),2) pct
FROM memory_index_chunks GROUP BY path ORDER BY c DESC LIMIT 20;
```

I alert above **6%** for a single file. That threshold is empirical, not principled.

### A4. Derivatives outrank their sources

Automatically generated material — promotion logs, nightly summaries, anything that
quotes source documents verbatim — accumulated to **82%** of the index at its worst,
and **32%** of it was one generator's working log. Counting *files* made this
invisible, because each generated file was small; counting chunks made it obvious.

Fix: move them **out of the index**, don't delete them. Archive, then re-index. The
assumption "old raw notes have already been promoted into curated notes" is exactly
the assumption that will bite you, so keep the originals reachable.

---

## B. Recency weighting

### B1. Touching a file is a ranking action

A/B with byte-identical content, only `mtime` differing:

```
file re-saved today          →  92%   (a neighbouring question's answer fell out of top-5)
same file, original mtime    →  96%
```

The question that broke was not about that file at all. The freshly-touched document
simply took third place in an unrelated query.

Consequences I now treat as rules:
- When you strengthen a node, **re-measure the neighbours too**, not just the target.
- If you revert content and the score doesn't come back, suspect `mtime`. Restoring
  the original timestamp for a document that did not really change is the *honest*
  action — printing an unchanged document as "just changed" is the lie.

> **Correction (2026-09-14).** "Only `mtime` differed" overstates what this A/B
> isolated. A week later I restored the `mtime` of eleven already-indexed notes and
> **not a single question moved.** The index keeps its own per-source record and is
> driven by content hashes; a pure `mtime` change on a file the index has already
> seen did not refresh what the ranker used. The round-24 restore landed in the same
> round as a content revert, which is what triggered the re-index. Revised rule:
> **check that the index's stored timestamp changed, not the file's.** The direction
> of B1 (recency is a ranking input you are touching whether you mean to or not)
> still holds; the clean "mtime alone" framing does not. See also G3 for where the
> timestamp actually comes from in later builds.

> **Correction (2026-11-03) to an earlier internal conclusion.** On 08-30 I had
> recorded recency weighting as "no measurable cost" (on/off tied on six recency
> questions). That was only true on the build where it could be switched off. From
> 2026.8.2 the setting is gone and the boost is always on; G2 shows what it costs on
> my corpus. The 08-30 verdict is refuted, not just outdated.

### B2. Recency boost can beat a better match on every component

A case where the losing document scored higher on **both** vector similarity and
text similarity, and still lost on the final blended score. The delta was added
after the components were combined. If your ranker exposes component scores, compare
them against the final ordering occasionally; a document that wins without winning
any component is telling you something.

---

## C. Interventions that did not work

### C1. Pruning the biggest hog: 0 points

Removing the largest space consumer from the index changed accuracy by **zero**. The
vacated slots were taken by the next-freshest documents. The competitor changed; the
crowding did not.

### C2. Removing an innocent file: −4 points

Taking an unrelated (but large) file out of the index cost 4 points, because the
freed slots went to recent, less relevant material. **Whatever moves, wins** — adding
and removing are both ranking actions.

### C3. So the prescription inverted

| intervention | effect |
|---|---|
| remove the crowding file | 0 points |
| remove an unrelated file | −4 points |
| **strengthen the node that should have won** | +4 points, and again +4 in a later round |

Strengthening means: put the answer in the node that *ought* to own it, with the
vocabulary the question uses, and let the touch-effect (B1) work for you instead of
against you.

---

## D. Measurement hazards

### D1. Your measurement log contaminates its own measurement

The document where I recorded round-by-round results lived in the indexed vault. It
grew to **41 chunks** and began appearing in results for questions it had nothing to
do with, pushing correct answers out. Keep evaluation records **outside the index**
(a separate git repo works well — history preserved, chunks not consumed).

### D2. "Not in top-5" is not "not in the corpus"

Widening `k` reorders results; a document absent at k=5 can be present and healthy at
k=10. Before diagnosing a broken index, change `k`.

### D3. Zero can be a broken gauge

I once built four months of reasoning on a counter that read 0. The pipeline
producing it had been dead the whole time. **Do not design on top of a zero you have
not independently reproduced.**

### D4. "not checked" is not "ok"

A status panel printed a component's line as un-measured, and I read the table as
all-green. Retrieval had been returning nothing for 25 minutes. Any status row is
either a *measurement* or a *setting* — split them before you read the table, and
carry "unknown" through to your summary instead of rounding it to healthy.

### D5. A number that only goes up is history, not status

Cumulative failure counters look like alarms and are not. Put a windowed value in the
status column and keep the cumulative one somewhere else.

### D5a. Count what changed between rounds before naming a culprit

A round once dropped 16 points (96% → 80%) right after I back-filled eleven days of
generated digests. I blamed the digests and the recency boost. A control round that
removed only the digests recovered half of it: the other half came from 22 unrelated
notes edited between the two rounds, which I had not counted. One `find -newer`
against the previous round's output would have listed them. **List the changes
first, then attribute.**

### D6. Confident-and-wrong is worse than nothing

Accuracy on the main set did not change when I removed generated artifacts — but the
top hit for a question with *no* correct answer moved from a generated artifact
(score 0.696, wrong document) to the genuinely relevant note (0.433). Aggregate
accuracy is blind to that improvement. Keep a few questions that *should* fail, and
look at what confidently answers them.

---

## E. Operating the thing

### E1. Redundancy hides failure

A fallback model provider was dead for **eleven days**. Nothing alerted, because the
primary kept working. When I finally looked at accumulated job failures, two of them
read `All models failed (2)` — the fallback had not been catching anything for days.
Read a fallback-activation log as a **first-order death signal**, not as reassurance.

### E2. Verify by running, not by reading

Syntax checks don't resolve names; reading a cron entry doesn't prove the command
string expands. Run the exact string the scheduler will run and check the exit code.

### E3. Don't put a timestamp in a generated file

I generated a daily statistics file with the generation time in its header. It
changed every day even when every measured value was identical, so the version
history could no longer answer "did anything actually change?" The commit already
carries the time.

### E4. Two stores always drift

The same threshold written in two scripts will diverge, and the divergence will be
silent. Keep the threshold in the tool that owns the measurement; let everything else
read its exit code. I nearly violated this while writing the gauge in this repo —
the file I was about to edit had a comment warning me not to.

---

## F. What I would tell someone starting today

1. Write the evaluation set first. Twenty-five questions is enough.
2. Add a per-file chunk-share gauge on day one. It is ten lines of SQL and it is the
   number that explains most surprises.
3. Prefer **one well-named node per concept** over a long index document. Long index
   documents fragment into many chunks and crowd the window.
4. Keep generated material out of the index by default; opt it back in deliberately.
5. Change one thing per round and re-run everything. The rounds that lose points are
   where the knowledge is.
6. When you upgrade the agent, take a fresh baseline and stop comparing across it
   (G1). Read the shipped ranking code rather than the docs or the config schema (G2).
7. Retire every question you have used to steer a fix, and keep a held-out set the
   fixes never see ([`evaluation-method.md`](evaluation-method.md) §8).

---

## G. After the 2026.9.7 upgrade (October 2026)

Everything above was measured on 2026.8.2 and 2026.9.2. In early October I moved to
2026.9.7, and in mid-October to 2026.10.5. The ranking code changed under me, so the
numbers in this section are **not comparable** with A–F.

### G1. An upgrade is a new baseline, not a regression

The 25 core questions scored 64–68% on 2026.9.2 at the end of September (they had
drifted down from 96% as the corpus grew; I did not isolate one cause). The first
baseline round on 2026.9.7 scored **44% (11/25)**, recency 1/6. The chunker version changed (3 → 5) and the index was rebuilt.

The more instructive number: on a 49-question set, the score went from 28/49 to
24/49 within days **with nothing changed on my side.** The curated notes simply
got older, and the recency boost discounted them further. A score can decay by the
clock alone.

### G2. The ranking knobs are constants

I rebuilt the search path offline by importing the shipped search functions and
replaying queries against a read-only copy of the index. On 2026.9.7 it reproduced
the live top-5 **85 of 85 slots, in order**. What it showed:

- Hybrid weights (vector 0.7 / text 0.3), the candidate multiplier, MMR (λ 0.7) and
  temporal decay (on, 30-day half-life) are **hard-coded**. The `memory.search`
  config has no fields for them; setting them in config does nothing.
- Even at k = 5 the ranker pulls a pool of 200 vector and 200 keyword candidates,
  blends them, runs MMR, then cuts.
- For Korean sentence queries the FTS5 path (all terms ANDed) usually returns
  nothing, so a fallback keyword scorer runs. On my 17-question probe, a median of
  169 of 200 keyword candidates saturated at the maximum score, so the text share was
  close to a constant and **the order was effectively decided by the vector score.**
- Flipping the constants in the replica, on those 17 questions:

  | variant | hits / 17 | MRR |
  |---|---|---|
  | live (hybrid + decay + MMR) | 13 | 0.50 |
  | hybrid + decay | 15 | 0.56 |
  | hybrid + MMR | 13 | 0.66 |
  | hybrid only | 16 | 0.76 |

  On my corpus the two always-on stages cost about three hits in seventeen and a
  third of the MRR. n = 17; read it as a direction.

After the 2026.10.5 upgrade the replica had to be rebuilt: the new build prefixes the
query embedding with a task string (`task: search result | query: `). With the prefix
the replica matched live **66/66**; without it, 1/66. Shifting the decay clock by 30
days gave 6/66 and turning MMR off gave 1/66. Those deliberate breakages are how I
know the 66/66 is not a loose match. I have not re-verified the constants on
2026.10.9.

### G3. Only curated notes age

The decay timestamp is not uniform. Daily notes named by date are aged by the date
in the filename; the always-loaded root memo and undated files in the memory folder
are exempt; **everything else, which means the curated ontology nodes, is aged by
the index's stored mtime.** In practice the notes I curate most carefully were the
only ones being discounted, while the root memo was never discounted at all.

### G4. So I pinned the age of curated nodes, and that contradicts B1

With no setting available, the only lever left was the timestamp. A daily job sets
the `mtime` of curated nodes to "now minus two days". It started with lessons on
10-01 and was extended to component, project and schema notes in round 39. The real
edit date lives in each note's frontmatter. Round 39 combined that extension with
four other changes, and went from 44% to **92% (23/25)** on the
core set and from 24/49 to **43/49** on the larger set, with **no question
dropping** and 19 rising.

Caveats, stated plainly:

- Five variables moved in that round. The replica decomposition attributes most of
  the gain to the age pinning; I did not cut the other four apart.
- This is the opposite of the "restore the honest timestamp" rule in B1. I accept
  that trade for curated nodes because they are meant to be evergreen and the decay
  is a constant I cannot change. I would not do it to anything dated.
- Even a pinned age is not neutral. During the day the age drifts from 2 to 3 days
  and lessons lose 4.5–6.7% of their score, which on my probe was larger than the
  typical gap between neighbouring top-5 results (~0.04).

### G5. Corpus growth since September

The index went from **1,640 chunks / 285 files** (late September) to **6,059 /
1,092** (early November), almost entirely from daily notes and project material.
The largest single file peaked at 8.4% of chunks in late September (a long
planning document) and is 4.1% now, under the 6% alarm. The September split quoted
in the README (56% curated / 39% generated / 5% root memo) is no longer current; I
have not re-measured it.

One small structural fix from this period: the root memo had six chunks containing
only a section heading. Merging each heading into its first item, with the character
count unchanged, cut the memo's share of result slots from 25.2% to 21.5% and
recovered one question.

---

## H. Does the graph itself help retrieval? Not shown.

A1 says the ontology moved accuracy +48 points. In September I tested which part of
it does the work. Before measuring I committed the criterion: **if typed links help
retrieval, removing them should hurt `multihop`.**

| arm | change | core 25 | multihop |
|---|---|---|---|
| A | as is (baseline) | 84% | 9/9 |
| B | remove predicate lines and generated backlink blocks (6.75% of the corpus) | 96% | 9/9 |
| C | remove only the generated backlink blocks (3.85%) | 84% | 8/9 |

`multihop` did not move, so by the pre-registered rule the graph's contribution to
retrieval is **not proven**. B's +12 points was unexpected. Arm C rules out "less
volume, so things reshuffled". The remaining guess (repetitive predicate lines blur
what distinguishes one note from another) was weakened later, when deleting 316
boilerplate predicate lines in the replica changed nothing.

How I read A1 now: what moved retrieval was **splitting knowledge into one
well-named note per concept**, the curated nodes. The typed links are useful to me
as a human and as an audit structure (`refuted-by` especially). I have no evidence
that they help the retriever.

---

## I. Corrections log

| date | earlier claim | now |
|---|---|---|
| 2026-08-30 → 2026-09-03 | recency weighting has no measurable cost | refuted: only true where it could be disabled; forced on from 2026.8.2 (B, G2) |
| 2026-08-30 → 2026-09-03 | "43 added lessons cost −16 points" | not reproduced on later builds: isolating 32 lessons made the score *worse* (C1-style), adding nine more did not lower it; don't use it to limit lesson growth |
| 2026-09-06 → 2026-09-14 | B1 isolates `mtime` alone | overstated: an `mtime`-only change on an indexed file did nothing (B1 note) |
| 2026-09-06 → 2026-10-07 | recency is "not disableable in this build" | broader: none of the hybrid/MMR/decay parameters are configurable through 2026.10.5 (G2) |
| 2026-08-22 → 2026-09-15 | the ontology's +48 is the graph | the curated split is shown; the graph's retrieval effect is not (H) |
