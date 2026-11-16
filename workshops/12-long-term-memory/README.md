# Workshop 12 — Long-term memory declined

Chapter 12 of the book. No solution is provided: you work in `my-agent/`.

## Goal

Decline long-term memory explicitly, and reread the application instead of relying on past conversations.

## Success criterion

A preference given in one conversation does not appear in the next one, and the agent does not promise to remember it. The interface announces it when each conversation opens. When a user mentions earlier work, the agent rereads the application instead of assuming a past conclusion.

## How to check

The end-to-end tests of this workshop are in [`tests/`](tests/). They stay red until the criterion is met. What can be checked by code (application state, traces, permissions, interface events) is checked first. When a criterion is about the quality of an answer, a written judge rubric applies; the meaning assessment will be calibrated in phase B.

```powershell
uv run --project workshop_kit/bootstrap workshop start 12
uv run --project workshop_kit/bootstrap workshop check 12
uv run --project workshop_kit/bootstrap workshop check 12 --non-regression   # workshops 03 to 12
```
