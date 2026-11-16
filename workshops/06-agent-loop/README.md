# Workshop 06 — Agent loop

Chapter 6 of the book. No solution is provided: you work in `my-agent/`.

## Goal

Turn the conversational loop into an agent loop that chains several model/tool cycles within one turn.

## Success criterion

Your agent chains several cycles within one turn and groups independent calls. At the cycle limit, it returns an answer that declares itself partial. Each ongoing step is reported to the interface, and an interruption stops the turn cleanly, with no new call. The trace lets you count the cycles of each turn.

## How to check

The end-to-end tests of this workshop are in [`tests/`](tests/). They stay red until the criterion is met. What can be checked by code (application state, traces, permissions, interface events) is checked first. When a criterion is about the quality of an answer, a written judge rubric applies; the meaning assessment will be calibrated in phase B.

```powershell
uv run --project workshop_kit/bootstrap workshop start 06
uv run --project workshop_kit/bootstrap workshop check 06
uv run --project workshop_kit/bootstrap workshop check 06 --non-regression   # workshops 03 to 06
```
