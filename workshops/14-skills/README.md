# Workshop 14 — Skills

Chapter 14 of the book. No solution is provided: you work in `my-agent/`. The versioned catalog is `my-agent/skills/`: `manifest.yaml` plus one folder per *skill* (read by the kit through the `skills_dir` setting).

## Goal

Package the business procedures as versioned skills, loaded on demand.

## Success criterion

Only the three skills of the versioned catalog load; a request for a skill foreign to the catalog is refused. A write tool is offered only after its skill is loaded, and always according to the user's permissions. A loaded skill is still present in the model input after a compaction.

## How to check

The end-to-end tests of this workshop are in [`tests/`](tests/). They stay red until the criterion is met. What can be checked by code (application state, traces, permissions, interface events) is checked first. When a criterion is about the quality of an answer, a written judge rubric applies; the meaning assessment will be calibrated in phase B.

```powershell
uv run --project workshop_kit/bootstrap workshop start 14
uv run --project workshop_kit/bootstrap workshop check 14
uv run --project workshop_kit/bootstrap workshop check 14 --non-regression   # workshops 03 to 14
```
