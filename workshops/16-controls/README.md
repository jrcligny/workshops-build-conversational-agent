# Workshop 16 — From instruction to control

Chapter 16 of the book. No solution is provided: you work in `my-agent/`.

## Goal

Move rules from the prompt into controls enforced by the harness.

## Success criterion

An answer based on a bounded result carries, below the answer, the mention built by the harness. When resolving a name returns several candidates, the current customer is recorded only after the user's choice. An order or an invoice cited without being among the consulted records is marked as unverified. Simultaneous conversations share neither working memory, nor loaded skills, nor marking, nor identity.

## How to check

The end-to-end tests of this workshop are in [`tests/`](tests/). They stay red until the criterion is met. What can be checked by code (application state, traces, permissions, interface events) is checked first. When a criterion is about the quality of an answer, a written judge rubric applies; the meaning assessment will be calibrated in phase B.

```powershell
uv run --project workshop_kit/bootstrap workshop start 16
uv run --project workshop_kit/bootstrap workshop check 16
uv run --project workshop_kit/bootstrap workshop check 16 --non-regression   # workshops 03 to 16
```
