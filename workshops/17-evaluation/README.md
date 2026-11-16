# Workshop 17 — Observe and evaluate

Chapter 17 of the book. No solution is provided: you work in `my-agent/`.

## Goal

Make every turn observable and build an evaluation route set for the edge cases of chapter 17.

## Success criterion

Every turn produces an end-to-end trace in which sensitive data is masked. Your route set covers the edge cases listed in the retained choice of chapter 17; each route is judged first on facts checked by code, then on meaning, and it is repeated. Running the set produces a report per route.

## Evaluation routes

The official route set lives in [`routes/`](routes/) (one file per route under `routes/cases/`), protected by the checksum `routes/routes.sha256`. Workshop 19 checks that it stays unchanged. Your route report goes to `my-agent/route-report.md`.

## How to check

The end-to-end tests of this workshop are in [`tests/`](tests/). They stay red until the criterion is met. What can be checked by code (application state, traces, permissions, interface events) is checked first. When a criterion is about the quality of an answer, a written judge rubric applies; the meaning assessment will be calibrated in phase B.

```powershell
uv run --project workshop_kit/bootstrap workshop start 17
uv run --project workshop_kit/bootstrap workshop check 17
uv run --project workshop_kit/bootstrap workshop check 17 --non-regression   # workshops 03 to 17
```
