# Agent memory that actually answers

Field notes from running an [OpenClaw](https://docs.openclaw.ai) agent as daily
infrastructure for ~6 months, and from turning its memory layer into something
measurable: a hand-built ontology as the corpus, local embeddings for retrieval,
and a 25-question evaluation set re-run **40 times** (plus six sub-rounds), one
change per round. Last updated 2026-11-03; see [`CHANGELOG.md`](CHANGELOG.md).

This repository is not a framework. It is **what the measurements said**, including
the parts where they contradicted what I expected.

> 한국어 전문: [`README.ko.md`](README.ko.md)

---

## The one-paragraph version

Retrieval quality was never limited by the embedding model or the search algorithm.
It was limited by **corpus structure** — how knowledge is split into files, how many
chunks each file produces, and which file happens to have been touched most recently.
Introducing a linked ontology moved answer accuracy **+48 points** in a single round.
After that, the dominant variable was **how many of the top-5 result slots one file
occupies**. And in the version I run, simply changing a file's `mtime` — with the
content byte-identical — moved the score **4 points** (a later check narrowed that
claim; see the correction under findings B1).

---

## Architecture

```
question
   │
   ├─ vector search   local llama.cpp server · embeddinggemma-300m (768-dim)
   └─ text search     SQLite FTS5 (unicode61)
   │
   ├─ hybrid rank 0.7/0.3  →  recency decay (30-day half-life)  →  MMR (λ 0.7)
   │      ↑ all three hard-coded in the builds I measured (through 2026.10.5)
   ▼
top-k chunks → agent context
```

| layer | choice | why |
|---|---|---|
| Embeddings | local `llama.cpp` managed server | no API key, no expiry, works offline. ~95 MB resident |
| Index | SQLite (FTS5 + vector table) alongside the agent DB | one file to back up; snapshot-able |
| Chunking | 400 tokens / 80 overlap | product default; the interesting variable turned out to be *file shape*, not chunk size |
| Corpus | a Markdown vault (Obsidian-style), indexed by path allowlist | plain files, git-diffable, editable by a human |
| Ontology | typed links between notes, hard cap of 8 predicates | see [`docs/ontology-schema.md`](docs/ontology-schema.md) |

In September roughly **56%** of my index was ontology-governed notes, **39%**
auto-generated daily material, **5%** the always-loaded root memo. Those proportions
mattered more than any tuning knob I found. The index has since grown from 1,640 to
6,059 chunks and I have not re-measured the split ([findings G5](docs/findings.md)).

---

## The method (this is the transferable part)

1. Write an evaluation set **before** tuning anything. Mine has 25 questions in four
   kinds: `fact`, `multihop`, `causal`, and `negative` (questions that *should* have
   no good answer).
2. Record, for each question, which document must be in the top-k for it to count.
3. **Change exactly one thing per round.** Re-run *all* questions, not just the one
   you were trying to fix.
4. Log every round — including the ones that got worse. Half of what I learned came
   from rounds that lost points.

Full method, including how I score and what I got wrong: [`docs/evaluation-method.md`](docs/evaluation-method.md)

Result over the first 25 rounds: **96%** on the auto-scored 25 (and `recency` 6/6).
It was not a monotonic climb. Rounds 21–23 lost 4 points and round 24 got them back
**without changing a single byte of content** (see the correction under findings B1).

After upgrading to 2026.9.7 the same questions started from **44%**: a new baseline,
not comparable with the old numbers. Round 39 brought them to **92%**. Since late
October, changes are judged on a separate held-out set that no fix has seen.

---

## Findings

The full list with numbers is in [`docs/findings.md`](docs/findings.md). The five
that changed how I work:

**1. Structure beats tuning.** Introducing the ontology: **+48 points**. Nothing I
did to the retriever afterwards came within an order of magnitude of that.

**2. Count chunks, not files — and count *slots*, not documents.** One file holding
2.03 of the top-5 slots per query correlated with 84%; getting it to 1.33 correlated
with 92%. File count and file size both hid this. A bullet-list document splits into
many small chunks and effectively buys more lottery tickets than a prose document of
the same size.

**3. Touching a file is a ranking action.** With recency weighting on and no way to
turn it off, editing — or merely re-saving — a note pushes it up for *every*
neighbouring query. I confirmed this with an A/B where the content was byte-identical
and only `mtime` differed: **92% vs 96%**. So "I improved a note and something else
broke" is not a paradox; it is the expected behaviour.
*(Correction 2026-09-14: an `mtime`-only change on an already-indexed file later
moved nothing. The round-24 restore coincided with a re-index. What matters is the
timestamp the index stores, not the file's. [B1](docs/findings.md))*

**4. Removing things doesn't work the way you'd hope.** Pruning the biggest space
hog changed accuracy by **0 points** — the freed slots went to the next-freshest
file. Removing an *innocent* file cost **−4 points**. The prescription that actually
worked was the opposite: **strengthen the node that should have won.**

**5. Your measurement log will contaminate your measurement.** My evaluation
write-up lives in the same vault as the corpus. It grew to 41 chunks and started
pushing correct answers out of the window. Measurement records belong **outside the
index**.

### Added since the first version (2026-11-03)

**6. The ranking knobs are constants, so read the shipped code.** An offline replica
built from the shipped search functions reproduced live results slot for slot. It
showed hybrid weights, MMR and the 30-day decay hard-coded, with no config field for
any of them. On a 17-question probe, the two always-on stages cost about 3 hits and
a third of the MRR. ([G2](docs/findings.md))

**7. Only curated notes age.** Dated daily notes are aged by their filename date and
the root memo is exempt, so the decay landed almost entirely on the curated nodes.
Pinning their age changed more than anything else I tried in October. That
contradicts finding 3's "honest timestamp" advice, and the findings say so.
([G3–G4](docs/findings.md))

**8. The graph's own retrieval effect is not shown.** Removing the typed predicate
lines did not hurt multi-hop questions, which was the pre-registered test. What the
+48 bought was the split into one note per concept. ([H](docs/findings.md))

---

## What's here you can actually run

- [`tools/index_census.py`](tools/index_census.py) — reads an OpenClaw memory index
  and prints total chunks, file count, and per-file chunk share; exits non-zero when
  a single file exceeds a share threshold. This is the gauge I wish I'd had on day 1.
- [`tools/evalset_run.py`](tools/evalset_run.py) — the round runner. Swap in your own
  questions and it works as-is. Its comments are mostly scar tissue: why stderr is
  captured, why `negative` questions are not auto-scored, why the measurement path is
  stamped into every output file.

Everything else in this repo is prose, deliberately. The scripts that manage my own
vault are shaped by my folder layout and would be a trap to copy.

---

## Honest limits

- **n = 1.** One corpus, one person, one embedding model. Treat the *directions* as
  transferable and the *numbers* as mine.
- **The evaluation set has a blind spot.** Every expected answer lives in a curated
  note, so an intervention that quietly loses knowledge held *only* in raw daily
  notes would score as harmless. It measures what it was built to measure.
- **5 of the 30 questions have never been scored.** The `negative` probes (questions
  that should have no good answer) are recorded but judged by hand, and I have not
  done that consistently. I report the auto-scored 25 separately for that reason.
  *(Corrected 2026-11-03: this line said "5 of the 25".)*
- Recency weighting is **forced on** in the builds I run (from 2026.8.2). An earlier
  internal note of mine called it cost-free. That was measured on a build where it
  could still be turned off, and it is refuted.
- **The core 25 have been taught to.** Most of them have steered at least one fix, so
  they now serve as a regression check. Improvements are judged on a held-out set
  ([method §8](docs/evaluation-method.md)).
- Upgrades change the ranking code. Numbers from different builds are not compared
  in these notes; each upgrade starts a new baseline.

---

## Korean summary / 국문 요약

에이전트 메모리를 「검색이 되는」 상태로 만들기까지의 실측 기록입니다.
핵심은 임베딩 모델이나 검색 알고리즘이 아니라 **코퍼스의 구조**였습니다 —
온톨로지 도입 한 번에 정답률 **+48%p**, 그 뒤로는 **한 파일이 상위 5칸 중
몇 칸을 먹는가**가 지배 변수였습니다. 최신성 가산을 끌 수 없는 판에서는
파일을 만지는 것 자체가 랭킹 행위였습니다. 2026.9.7 이후로는 혼합 가중치·MMR·감쇠가
전부 상수이고, 감쇠는 큐레이션 노트에만 걸린다는 것도 확인했습니다.
방법론은 `docs/evaluation-method.md`, 수치가 붙은 발견 목록은 `docs/findings.md`
에 있습니다.

---

MIT licensed. Corrections and contradicting measurements are welcome — especially
contradicting ones.
