# Skills catalog (empty base)

Versioned storage for workshop 14. You edit this folder; the kit reads it
through `agent_sdk/src/agent_sdk/skills.py` (setting `skills_dir`,
default `my-agent/skills`). Expected format:

- `manifest.yaml` at the root, with a `skills` list;
- one folder per *skill* next to it, `my-agent/skills/<id>/`, containing at least a
  `SKILL.md` file (instructions) and, if needed, related resources.

Example entry, to add only when you write the *skill*:

```yaml
version: "1"
skills:
  - id: invoice-check
    title: Invoice check
    version: "1.0"
    path: invoice-check
```

The catalog shipped with the shell is **empty**: no *skill* is provided.
