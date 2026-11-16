# Workshop 11 — A single agent: queries on the trace

Chapter 11 of the book. No solution is provided: you work in `my-agent/`.

## Goal

Keep a single agent and express two review criteria as queries on the trace.

## Success criterion

The agent stays single, with no sub-agent and no routing; there is nothing to add to its code. The deliverable expresses two review criteria as queries on the trace: the share of the context taken by intermediate reads, turn by turn, and the presence, within one turn, of domains with incompatible permissions. These queries run on the traces produced by your runs (module `my-agent/trace_queries.py`).

## How to check

The end-to-end tests of this workshop are in [`tests/`](tests/). They stay red until the criterion is met. What can be checked by code (application state, traces, permissions, interface events) is checked first. When a criterion is about the quality of an answer, a written judge rubric applies; the meaning assessment will be calibrated in phase B.

```powershell
uv run --project workshop_kit/bootstrap workshop start 11
uv run --project workshop_kit/bootstrap workshop check 11
uv run --project workshop_kit/bootstrap workshop check 11 --non-regression   # workshops 03 to 11
```
