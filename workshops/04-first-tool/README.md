# Workshop 04 — First tool

Chapter 4 of the book. No solution is provided: you work in `my-agent/`.

## Goal

Give your agent its first tool: looking up one order.

## Success criterion

Your agent looks up an order with its first tool. An exact reference is found directly; an approximate reference gives the closest order, and the answer reports the difference. An excluded order appears neither in a direct lookup nor among the suggestions. The result distinguishes success, missing data and error, and the agent makes at most one tool call per message.

## How to check

The end-to-end tests of this workshop are in [`tests/`](tests/). They stay red until the criterion is met. What can be checked by code (application state, traces, permissions, interface events) is checked first. When a criterion is about the quality of an answer, a written judge rubric applies; the meaning assessment will be calibrated in phase B.

```powershell
uv run workshop start 04
uv run workshop check 04
uv run workshop check 04 --non-regression   # workshops 03 to 04
```
