# Workshop 10b — Writes

Chapter 10 of the book. No solution is provided: you work in `my-agent/`.

## Goal

Add the two preparation tools (purchase request, invoice approval), with a confirmation gesture before any submission.

## Success criterion

The two preparation tools are offered only to users who have the permission, and the server refuses their call for everybody else. A draft has no effect until the user confirms it with a gesture in the interface. The submission comes from the harness, with the user's permissions, and the application assigns it to the agent on behalf of that person. No answer announces an action as done before the submission.

## How to check

The end-to-end tests of this workshop are in [`tests/`](tests/). They stay red until the criterion is met. What can be checked by code (application state, traces, permissions, interface events) is checked first. When a criterion is about the quality of an answer, a written judge rubric applies; the meaning assessment will be calibrated in phase B.

```powershell
uv run workshop start 10b
uv run workshop check 10b
uv run workshop check 10b --non-regression   # workshops 03 to 10b
```
