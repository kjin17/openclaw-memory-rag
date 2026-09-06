# The ontology

A "knowledge graph" for an agent's memory does not need a triple store. Mine is
Markdown files with a handful of typed links, and it produced the single largest
retrieval improvement I measured (**+48 points**, see [`findings.md`](findings.md)).

The design constraints below are the parts that turned out to matter.

---

## Node types

| type | folder | holds | typical size |
|---|---|---|---|
| **Component** | `08_Components/` | one moving part — a job, a service, an API | 1–3 chunks |
| **Project** | `01_Projects/` | one ongoing effort, its state and landmines | 3–10 chunks |
| **Incident** | `06_Incidents/` | one thing that broke, with the timeline | 2–4 chunks |
| **Lesson** | `00_Ontology/Lessons/` | one transferable rule, with the evidence | 1–3 chunks |
| **Schema / dashboard** | `00_Ontology/` | the map, the gauges, the evaluation record | small |

Everything else — dated notes, generated summaries — is *not* a node. It is raw
material that may later be promoted into one.

---

## Rule 1: cap the predicates

Eight. Mine are effectively:

```
상위::      belongs-to        (parent node — every node has exactly one)
의존::      depends-on        (component → component)
영향::      affects           (lesson → what it changes)
반증::      refuted-by        (lesson → the observation that contradicts it)
```

…plus a few situational ones. **The cap is the feature.** Every new predicate is a
new way for two authors (or the same author on two days) to encode the same idea
differently, and an unused predicate is worse than no predicate: it makes the graph
look richer than it is.

## Rule 2: values are links, never prose

`의존:: [[08_Components/scheduler]]`, not `의존:: the scheduler`. Prose values don't
resolve, don't get caught by a link checker, and quietly rot.

## Rule 3: edges must be written in both directions

Backlinks computed by your note-taking app are invisible to the *index*. If a hub
note relies on a query to list its children, then to the retriever that hub note is
**empty** — and hub notes are exactly the ones you want retrieved. Write the edge on
both ends, and run a checker that counts unresolved links.

## Rule 4: one concept, one node, one owner

If a fact lives in two places it will diverge, and the retriever will surface
whichever was touched more recently — not whichever is correct. When you find a
duplicate, pick an owner and make the other side a link.

## Rule 5: a lesson is not a log

A lesson node states a rule, the evidence for it, and **what would refute it**. It is
not a diary entry. Concretely, mine look like:

```markdown
---
name: removing-content-feeds-the-freshest-file
description: pruning the crowding file gave 0 points; the freed slots went to whatever was newest
---

<the observation, with numbers>

**Why:** <mechanism>

**How to apply:** <what to do differently>

⚠️ <the case where this does not hold>

related: [[touching-a-file-is-a-ranking-action]]
```

The `description` line is doing retrieval work, not decoration — it is often what
matches the query.

---

## What the ontology costs

Be honest about this before adopting it:

- **Nodes are chunks.** Every node you add competes with every other node for the
  result window. A graph with 400 thin nodes is not obviously better than one with
  100 solid ones; I have not measured the crossover.
- **Maintenance is real.** Unresolved links, stale duplicates, and hub notes that
  drifted empty all need a checker. Manual discipline does not survive a busy week —
  I have the failed attempt on record.
- **Touching nodes moves rankings.** Reorganising the graph is never a no-op for
  retrieval quality. Re-measure after structural edits.

---

## Minimal starting shape

If you want the effect without the apparatus:

1. Make a `components/` folder. One file per moving part. Name the file the way you'd
   say the thing out loud.
2. Give every file one parent link and, where true, one depends-on link.
3. Make a `lessons/` folder with the format above.
4. Add a link checker that fails when a `[[link]]` has no target.
5. Stop there until an evaluation set tells you what's missing.

Step 5 is the one people skip.
