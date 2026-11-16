# Workshop 05 — Two read tools

Chapter 5 of the book. No solution is provided: you work in `my-agent/`.

## Goal

Add two read tools: searching for a customer and listing a customer's orders.

## Success criterion

Your agent has two new read tools. Searching for a customer returns every matching customer, namesakes included, without picking one on behalf of the user. The list of a customer's orders can keep only those whose delivery is late, and the filter is applied by the tool, not by the model.

## How to check

The end-to-end tests of this workshop are in [`tests/`](tests/). They stay red until the criterion is met. What can be checked by code (application state, traces, permissions, interface events) is checked first. When a criterion is about the quality of an answer, a written judge rubric applies; the meaning assessment will be calibrated in phase B.

```powershell
uv run workshop start 05
uv run workshop check 05
uv run workshop check 05 --non-regression   # workshops 03 to 05
```
