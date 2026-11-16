# Workshop 18 — Failures and delivery

Chapter 18 of the book. No solution is provided: you work in `my-agent/`.

## Goal

Handle failures: a single fallback to a backup model, safe retries for reads only, and versions in the trace.

## Success criterion

When the primary model is unavailable, your agent switches once to the fallback model; if the failure persists, it ends the answer cleanly. A read may be retried; a submission never is, and the user is invited to check in the application. The trace carries the version of the instructions, of the skills catalog, of the tool definitions and of the document index.

## How to check

The end-to-end tests of this workshop are in [`tests/`](tests/). They stay red until the criterion is met. What can be checked by code (application state, traces, permissions, interface events) is checked first. When a criterion is about the quality of an answer, a written judge rubric applies; the meaning assessment will be calibrated in phase B.

```powershell
uv run --project workshop_kit/bootstrap workshop start 18
uv run --project workshop_kit/bootstrap workshop check 18
uv run --project workshop_kit/bootstrap workshop check 18 --non-regression   # workshops 03 to 18
```
