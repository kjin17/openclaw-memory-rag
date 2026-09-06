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
