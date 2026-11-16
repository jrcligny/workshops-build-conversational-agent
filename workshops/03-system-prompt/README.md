# Workshop 03 — System prompt and conversational loop

Chapter 3 of the book. No solution is provided: you work in `my-agent/`.

## Goal

Write the first version of your harness: a short system prompt and a conversational loop that replays the history on every turn, with no tool yet.

## Success criterion

Your agent answers with a short system prompt, without any tool or application documentation, and replays the history on every turn. Asked about the status of a specific order, it answers that it does not have that information, including when the user insists (assessed by the judge over repeated runs). Every turn complies with the interface contract and leaves its minimal trace.

## How to check

The end-to-end tests of this workshop are in [`tests/`](tests/). They stay red until the criterion is met. What can be checked by code (application state, traces, permissions, interface events) is checked first. When a criterion is about the quality of an answer, a written judge rubric applies; the meaning assessment will be calibrated in phase B.

```powershell
uv run --project workshop_kit/bootstrap workshop start 03
uv run --project workshop_kit/bootstrap workshop check 03
uv run --project workshop_kit/bootstrap workshop check 03 --non-regression   # workshops 03 to 03
```
