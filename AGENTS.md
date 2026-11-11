# AGENTS.md

This repository is a public technical whitepaper. Read this before editing.

## Scope
- In: how OpenClaw memory search (RAG) is used here (structure, configuration, method,
  measurement procedure) and what it measured, including refuted results.
- Out: operational anecdotes, incident narratives, personal environment details,
  general operations notes that are not about retrieval.

## Never publish
- Addresses, IPs, hostnames, ports tied to a person's machines, people's names, home or
  device details, amounts of money, tokens or keys, private repository names.
- Question text from the held-out set (publish counts and IDs only).

## Numbers
- Every number must be re-checked against the raw measurement (round result files,
  evaluation-set table) before it is written or changed.
- Never delete a refuted number. Mark it, date it, and add a row to the corrections log
  (whitepaper §5.2).
- Do not compare numbers across OpenClaw builds or measuring-tool changes.

## Layout
- `docs/whitepaper.md` is canonical; `docs/whitepaper.ko.md` mirrors its sections.
- `README*.md` stay short: summary and links. Record every change in `CHANGELOG.md`.

## Before push
1. `git status` and add files by name (never `git add .` / `-A`).
2. `git diff --cached` and read it for secrets and private details.
3. `gitleaks git --log-opts="origin/main..HEAD"` must report no leaks.
4. `python3 -I -m py_compile tools/*.py`
5. A separate reviewer (not the author) checks the diff and gives a pass before merge.
