# Workshop 07 — Context and compaction

Chapter 7 of the book. No solution is provided: you work in `my-agent/`.

## Goal

Keep the context under control: bounded tool results, and compaction of the conversation beyond a threshold.

## Success criterion

The order list returns a limited number of lines together with the total, declares that this total is a minimum when the cap is reached, and offers a count mode; the answer announces that it is partial. Beyond the threshold, the history is compacted: the trace contains the event, the interface reports it, and the model input contains the summary as well as, verbatim, the initial request and the user's messages (only old answers and old tool results are summarized). Below the threshold, no compaction happens.

## How to check

The end-to-end tests of this workshop are in [`tests/`](tests/). They stay red until the criterion is met. What can be checked by code (application state, traces, permissions, interface events) is checked first. When a criterion is about the quality of an answer, a written judge rubric applies; the meaning assessment will be calibrated in phase B.

```powershell
uv run workshop start 07
uv run workshop check 07
uv run workshop check 07 --non-regression   # workshops 03 to 07
```
