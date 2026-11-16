# Workshop 15 — Read without obeying

Chapter 15 of the book. No solution is provided: you work in `my-agent/`. Attached documents go to `my-agent/attachments/` (read by the kit through the `attachments_dir` setting); the tests use their own fixture in `tests/fixtures/`.

## Goal

Read untrusted attachments without letting their content drive the agent's actions.

## Success criterion

Your agent reads an attachment by its id, in the reserved area, read-only, and only if the user may view the record it is attached to. After reading untrusted content, the write tools disappear until the end of the turn: "read this quote and prepare the purchase request" first gives a reading report. The agent has no sending tool, and caches are shared neither between users nor between organizations.

## How to check

The end-to-end tests of this workshop are in [`tests/`](tests/). They stay red until the criterion is met. What can be checked by code (application state, traces, permissions, interface events) is checked first. When a criterion is about the quality of an answer, a written judge rubric applies; the meaning assessment will be calibrated in phase B.

```powershell
uv run --project workshop_kit/bootstrap workshop start 15
uv run --project workshop_kit/bootstrap workshop check 15
uv run --project workshop_kit/bootstrap workshop check 15 --non-regression   # workshops 03 to 15
```
