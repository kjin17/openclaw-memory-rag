# Measuring and shaping retrieval in an agent's memory

A technical whitepaper on how we use [OpenClaw](https://docs.openclaw.ai)'s built-in
memory search (RAG) as an agent's long-term memory, how we measure it, and what the
measurements showed, including the results that contradicted earlier claims.

**Read the whitepaper: [`docs/whitepaper.md`](docs/whitepaper.md)** (version 2026-11-09)
· 한국어: [`README.ko.md`](README.ko.md), [`docs/whitepaper.ko.md`](docs/whitepaper.ko.md)

---

## Summary

- **Setup.** A Markdown vault indexed by OpenClaw memory search: local
  `embeddinggemma-300m` embeddings via `llama.cpp`, SQLite FTS5, hybrid ranking with
  temporal decay and MMR. Knowledge is split into one curated note per concept.
- **Method.** A 25-question evaluation set written before tuning, re-run in full after
  every single change (45 rounds), plus a held-out set, a fixed-baseline regression
  check, a stale-value probe, and an offline replica of the shipped ranking code.
- **Results.**
  - Splitting knowledge into curated notes: **40% → 88%** in one round.
  - Afterwards the dominant variable was how many of the top-5 slots one file takes
    (2.03 slots → 84%, 1.33 slots → 92%).
  - Hybrid weights, MMR and the 30-day decay are hard-coded; on our probe the two
    always-on stages cost about 3 of 17 hits.
  - Only curated notes are aged by the decay; pinning their age took the core set from
    44% to 92% on 2026.9.7 (five variables moved in that round; the replica
    attributes most of the gain to pinning).
  - The typed graph links themselves have no shown retrieval effect.
  - Since 2026-11-03: documentation fixes moved the first-ranked stale chunk from 7 to
    4 of 15 changed facts (2026-11-07 → 11-09), and in-line correction markers took
    old claims returned with neither a correction nor a counter-example from 4 to 0 of
    20 queries (2026-11-06 → 11-09).
- **Limits.** n = 1 corpus and model; numbers from different builds are not compared.
  Refuted claims stay in the text, marked and dated.

## Contents

| document | what it covers |
|---|---|
| [`docs/whitepaper.md`](docs/whitepaper.md) | abstract, background, architecture, method, results, limits and refutations, reproduction |
| [`docs/evaluation-method.md`](docs/evaluation-method.md) | Appendix A: the evaluation method in detail |
| [`docs/ontology-schema.md`](docs/ontology-schema.md) | Appendix B: the note schema and its costs |
| [`tools/index_census.py`](tools/index_census.py) | per-file chunk-share gauge for an OpenClaw memory index |
| [`tools/evalset_run.py`](tools/evalset_run.py) | the round runner (replace the questions with your own) |
| [`CHANGELOG.md`](CHANGELOG.md) | change history |

`docs/findings.md` from earlier versions now points into the whitepaper; finding IDs
(A1, B1, G2, H …) are unchanged.

---

MIT licensed. Contradicting measurements are especially welcome.
