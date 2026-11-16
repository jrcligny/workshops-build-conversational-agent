# Evaluation routes

The official routes of chapter 17, once published here, must not be modified
by the tool of workshop 19. A reserved part is not distributed in this
repository and must stay out of reach of the local mode.

Place one file per route under `cases/`. The file `routes.sha256` lets you
check the integrity of this folder; regenerate it only when the team changes
the routes. Run this command from the repository root, using the separate
test environment (not the tooling or an application's environment):

```powershell
uv run --project workshop_tests python -m workshop_tests.evaluation.routes --write
```

The digest covers the relative path and the content of every file except
`routes.sha256`, with line endings normalised to LF, so it is identical on
Windows and Linux.
