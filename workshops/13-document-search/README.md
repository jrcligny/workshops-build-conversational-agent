# Workshop 13 — Document search

Chapter 13 of the book. No solution is provided: you work in `my-agent/`.

## Goal

Add a document search tool backed by the repository's search application.

## Success criterion

Your document search tool queries the repository's search application, on demand. It returns passages filtered by permissions and organization, and explicitly declares an empty result. The displayed sources are established by the program, and a retired version no longer appears after the index is rebuilt. The answer distinguishes what comes from the documentation from what comes from the data.

## How to check

The end-to-end tests of this workshop are in [`tests/`](tests/). They stay red until the criterion is met. What can be checked by code (application state, traces, permissions, interface events) is checked first. When a criterion is about the quality of an answer, a written judge rubric applies; the meaning assessment will be calibrated in phase B.

```powershell
uv run --project workshop_kit/bootstrap workshop start 13
uv run --project workshop_kit/bootstrap workshop check 13
uv run --project workshop_kit/bootstrap workshop check 13 --non-regression   # workshops 03 to 13
```
