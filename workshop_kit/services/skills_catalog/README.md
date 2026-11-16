# Skills catalog (empty base)

Versioned storage for workshop 14. Expected format:

- `manifest.yaml` at the root, with a `skills` list;
- one folder per *skill* under `skills/<id>/`, containing at least a
  `SKILL.md` file (instructions) and, if needed, related resources.

Example entry, to add only when you write the *skill*:

```yaml
version: "1"
skills:
  - id: invoice-check
    title: Invoice check
    version: "1.0"
    path: skills/invoice-check
```

The catalog shipped with the shell is **empty**: no *skill* is provided.
