# Workshop 08 — Working memory

Chapter 8 of the book. No solution is provided: you work in `my-agent/`.

## Goal

Give your agent a working memory: an explicit conversation state that survives compaction.

## Success criterion

After a compaction, your agent still knows which customer and which order are current, including when the customer was chosen between two namesakes: the conversation state appears in the trace, distinct from the summary. When another customer is designated unambiguously, the previous one stops being the current customer.

## How to check

The end-to-end tests of this workshop are in [`tests/`](tests/). They stay red until the criterion is met. What can be checked by code (application state, traces, permissions, interface events) is checked first. When a criterion is about the quality of an answer, a written judge rubric applies; the meaning assessment will be calibrated in phase B.

```powershell
uv run workshop start 08
uv run workshop check 08
uv run workshop check 08 --non-regression   # workshops 03 to 08
```
