# Workshop 10d — Sandboxing

Chapter 10 of the book. No solution is provided: you work in `my-agent/`. The sandbox policy to fill in is `my-agent/sandbox/policy.yaml` (read by the kit through the `sandbox_policy_file` setting).

## Goal

Sandbox the tool server and bound each turn in duration and budget.

## Success criterion

The tool server accesses no file, and a destination missing from the allowlist is refused. A turn that reaches its duration or budget limit stops and shows what it obtained and what is missing. No secret appears in the model input or in the trace.

## How to check

The end-to-end tests of this workshop are in [`tests/`](tests/). They stay red until the criterion is met. What can be checked by code (application state, traces, permissions, interface events) is checked first. When a criterion is about the quality of an answer, a written judge rubric applies; the meaning assessment will be calibrated in phase B.

```powershell
uv run workshop start 10d
uv run workshop check 10d
uv run workshop check 10d --non-regression   # workshops 03 to 10d
```
