# Workshop 10c — Groupings

Chapter 10 of the book. No solution is provided: you work in `my-agent/`.

## Goal

Answer grouping and aggregate questions through the query tool, never by running code produced by the model.

## Success criterion

A grouping question is computed by the query tool, and its result is bounded and declared. No code produced by the model is executed. Asked for a median, the agent answers that it cannot compute it and offers the available aggregates.

## How to check

The end-to-end tests of this workshop are in [`tests/`](tests/). They stay red until the criterion is met. What can be checked by code (application state, traces, permissions, interface events) is checked first. When a criterion is about the quality of an answer, a written judge rubric applies; the meaning assessment will be calibrated in phase B.

```powershell
uv run workshop start 10c
uv run workshop check 10c
uv run workshop check 10c --non-regression   # workshops 03 to 10c
```
