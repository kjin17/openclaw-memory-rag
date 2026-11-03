# How I evaluate a memory layer

Twenty-five questions, four kinds, re-run in full after every single change. That's
the whole method. The discipline is in the details below — and in the parts I got
wrong.

---

## 1. Build the set before you tune anything

If you tune first, you will "improve" the system and have no way to know. I write
each question with the document that **must** appear in the top-k for the answer to
be reachable.

| kind | n | what it catches |
|---|---|---|
| `fact` | 8 | can it find a stated value at all |
| `multihop` | 9 | does it retrieve two documents that must be combined |
| `causal` | 8 | can it reach the *reason*, which usually lives in a different node than the symptom |
| `negative` | 5 | what confidently answers a question that has **no** good answer |
| `recency` | 6 | (added later) questions about recent events, to price the recency weighting |
| larger probes | 17, 54 | (added from late September) occupancy probes, the 54-question one with 49 auto-scored, read at k = 5, 6 and 20, to see *how far* outside the window a missed answer sits |

Scoring is mechanical: the expected document is in the top-k, or it isn't. I do not
grade the prose. Prose grading turns a repeatable measurement into an opinion.

## 2. One change per round. Re-run everything.

The temptation is to re-run only the question you were fixing. Every time I gave in
to it I missed a regression somewhere else — and the regressions were usually in
questions that had nothing to do with the file I touched (see the recency finding).

I violated this rule three times in one day early on and could not attribute any of
the results. Those rounds are recorded as unusable.

## 3. Log every round, including the bad ones

```
round | date  | what changed                          | score | note
20    | 09-06 | strengthened a component note         | 96%   | multihop 9/9, record
21-23 | 09-06 | edited → shrank → reverted one file   | 92%   | target unfixed, an unrelated fact broke
24    | 09-06 | restored that file's original mtime   | 96%   | content byte-identical
```

Rows 21–24 are the most valuable four rows in my table, and every one of them is a
failure or a reversal.

## 4. Keep the log out of the index

My evaluation write-up lived in the indexed vault and grew to 41 chunks, at which
point it started appearing in results for unrelated questions and pushing correct
answers out of the window. **The measurement was degrading the thing it measured.**

Move round records to a separate repository. You keep the history and stop paying
for it in retrieval.

## 5. Measure the neighbours, not just the target

Because touching a file lifts it for *every* nearby query, an intervention that fixes
your target question can break two others. A round is only "good" if the whole set
holds.

## 6. Watch the harness itself

Two harness problems cost me real time:

- **The measurement path matters.** Running the query through a CLI that took a lock
  added stalls of ~52 seconds to some rounds; the same query through the service API
  took ~1 second. Latency numbers from before and after that switch are not
  comparable, and I annotate the table where the path changed.
- **A stalled outlier is not slow work.** The 52-second figure was a lock timeout,
  not computation. When a duration clusters on a suspiciously round constant, look
  for a timeout before you look for a bottleneck.

## 7. Things my set cannot see (state these out loud)

- Every expected document is a **curated** note. An intervention that loses knowledge
  held only in raw daily notes scores as harmless. The set measures what it was built
  to measure.
- The 5 `negative` questions have **never been consistently scored**. They are
  recorded, and judged by hand when I remember. I report the auto-scored 25 separately
  so the headline number isn't quietly borrowing credit from unscored questions.
- n = 1 corpus, 1 embedding model, 1 person writing both the questions and the notes.
  Directions transfer; numbers don't.
- **The core set has been taught to.** By late October most of the 25 had been the
  target of at least one fix. A question you steered a change by is no longer a fair
  ruler for that kind of change. See §8.

## 8. Keep a held-out set, and retire questions you fixed toward

After about forty rounds I sorted every question into three groups:

- **used**: I changed the corpus specifically to make it pass. Kept as a regression
  check, never as evidence that a change helped.
- **near-ceiling**: passes almost always. Good for catching regressions, too weak to
  measure improvements.
- **held out**: a new set of 15 questions (13 auto-scored, 2 `negative`), stored
  **outside the index**, pinned by a content hash, and read by the harness through
  an import. If I ever look at a held-out question while fixing something, it moves
  to "used" and gets replaced.

Two rules came with it. With n = 13, I only treat a difference of **two or more
questions** as signal. And while many small changes land in the same week, I measure
the held-out set once a week instead of after every change, and only split up the
week's changes when the weekly number moves by two or more. The baseline is written
into the round table on the day it is taken (11/13, MRR 0.75), not left in a results
file, so the next comparison does not require re-scoring raw output.

## 9. An offline replica is a better A/B than the live system, if you prove it first

The ranking constants are not configurable (see findings G2), so most "what if"
questions can only be answered offline. Copy the index read-only, import the shipped
search functions, replay the queries, and flip one stage at a time. This leaves the
live system untouched and makes runs repeatable.

None of that is worth anything until the replica matches live **slot for slot**.
Mine matched 85/85 on one build and then silently stopped matching after an upgrade,
which added a query prefix to the embedding input. Before trusting a replica:

1. Count how many questions match live exactly, top-k in order. Re-count after
   every agent upgrade.
2. Break it on purpose (drop the prefix, shift the decay clock, turn MMR off) and
   check that the match collapses. A replica that still "matches" when broken is not
   measuring anything.
3. Keep the replica in a repository, not in `/tmp`. Mine was lost to a reboot
   right when I needed it.

## 10. Number rounds once

Six rounds from one week were never entered in the table, and their result files
were numbered as if they came next. Weeks later the same numbers were reused. I
slotted them in as sub-rounds (36-1 … 36-6) in time order and kept the file names.
A round number is an identifier; allocate it when the round runs, not when you
write it up.

---

## Minimal harness

You need less than you think. Mine is one file that, per question, calls the search
API and checks whether the expected path is in the returned set:

```python
rows = []
for q in QUESTIONS:                       # {"q":…, "kind":…, "expect":[path, …]}
    hits = search(q["q"], k=5)            # → [path, …]
    ok = any(e in h for e in q["expect"] for h in hits)
    rows.append({**q, "hits": hits, "score": ok})

by_kind = collections.Counter(r["kind"] for r in rows if r["score"])
json.dump({"label": ROUND, "path": "api", "rows": rows}, open(f"{ROUND}.json", "w"),
          ensure_ascii=False)
```

Three things this deliberately does:

1. **Stores the raw hits**, not just pass/fail — you will want to know *what* won.
2. **Stamps the measurement path** (`"api"` vs `"cli"`) so future-you doesn't compare
   incomparable latencies.
3. Writes one file per round and never overwrites. The trend is the point.
