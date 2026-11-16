# Workshop 09 — Tool contract and MCP

Chapter 9 of the book. No solution is provided: you work in `my-agent/`.

## Goal

Move your read tools to your MCP server, built from the repository's empty server, and replace the specialised tools with a generic query tool.

## Success criterion

Your read tools are served by your MCP server, built from the repository's empty server, stateless; the agent no longer calls the application directly. Two distinct clients get the same catalog, from which the two tools of chapter 5 that were replaced have disappeared. A malformed filter receives an error that says what to fix, and values come back with their business label. A simple question from a buyer or an accountant succeeds through the generic query tool.

## How to check

The end-to-end tests of this workshop are in [`tests/`](tests/). They stay red until the criterion is met. What can be checked by code (application state, traces, permissions, interface events) is checked first. When a criterion is about the quality of an answer, a written judge rubric applies; the meaning assessment will be calibrated in phase B.

```powershell
uv run workshop start 09
uv run workshop check 09
uv run workshop check 09 --non-regression   # workshops 03 to 09
```
