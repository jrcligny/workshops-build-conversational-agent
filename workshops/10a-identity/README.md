# Workshop 10a — Identity and token exchange

Chapter 10 of the book. No solution is provided: you work in `my-agent/`.

## Goal

Make the tool server act on behalf of the user, never as a service account.

## Success criterion

The tool server refuses a request without a valid identity. For a valid request, it checks the token received and exchanges it for a distinct token, issued for the application on behalf of the user; the application sees the user, never a service account.

## How to check

The end-to-end tests of this workshop are in [`tests/`](tests/). They stay red until the criterion is met. What can be checked by code (application state, traces, permissions, interface events) is checked first. When a criterion is about the quality of an answer, a written judge rubric applies; the meaning assessment will be calibrated in phase B.

```powershell
uv run --project workshop_kit/bootstrap workshop start 10a
uv run --project workshop_kit/bootstrap workshop check 10a
uv run --project workshop_kit/bootstrap workshop check 10a --non-regression   # workshops 03 to 10a
```
