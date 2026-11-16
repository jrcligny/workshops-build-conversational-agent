# Workshop 19 — Specify a control

Chapter 19 of the book. No solution is provided: you work in `my-agent/`.

## Goal

Specify, implement and test one harness control, optionally with a coding agent.

## Success criterion

You write the short specification of a harness control, then its implementation and its checks, at least one of which feeds the harness a deliberately wrong model output. Using a coding agent is optional. The route set is not modified and its reserved part stays out of reach of the tool.

## How to check

The end-to-end tests of this workshop are in [`tests/`](tests/). They stay red until the criterion is met. What can be checked by code (application state, traces, permissions, interface events) is checked first. When a criterion is about the quality of an answer, a written judge rubric applies; the meaning assessment will be calibrated in phase B.

```powershell
uv run --project workshop_kit/bootstrap workshop start 19
uv run --project workshop_kit/bootstrap workshop check 19
uv run --project workshop_kit/bootstrap workshop check 19 --non-regression   # workshops 03 to 19
```
