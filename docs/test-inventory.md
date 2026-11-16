# Workshop test inventory

Aligned with the "success criterion" subsections of the book
(`jrcligny/ai-generated-books`, branch `relecture/alignement-ateliers`, not yet merged
into `main`). All these tests **fail on the empty shell** and **against the inert agent**
(`workshop check-shell`, `workshop check-inert`). The infrastructure tests in
`workshop_kit/tests/` must pass. Shared fixtures, clients, runtime probes and evaluation
helpers live in `workshop_tests/testing/` and `workshop_tests/evaluation/`, not in the
runtime kit. The names each test reads are listed in
[interface-contract.md](interface-contract.md#names-read-by-the-tests).

The user turns and expected phrases are French: the agent converses in
French (see `docs/decisions.md`, Language). Judge rubrics fail an answer that
is not in French.

Facts checked by code (application state, call logs, traces, interface events, runtime
probes) come first. A rubric then judges the meaning: structural requirements, then a
judge model when configured (`JUDGE_MODE`). "Repeated" means the k out of n rule
(`JUDGE_K` out of `JUDGE_N`, see `docs/decisions.md`).

| Workshop | Tests folder | Tests (facts checked by code) | Judge (rubric) |
|---|---|---|---|
| 03 | `workshops/03-system-prompt/tests/` | Short prompt, no tool nor documentation; answer from a model call; no business call; history replayed; `superseded_by("04")`: no tool yet | Refusal to report on an order, including under insistence (repeated, superseded by 04) |
| 04 | `workshops/04-first-tool/tests/` | Exactly one call; `ok` / `approximate` with a suggestion / `not_found` without suggestion for a deleted order; invalid reference rejected before any application call | — |
| 05 | `workshops/05-read-tools/tests/` | Both namesakes returned, no order chosen for the user; `filter="late"` applied by the tool, total equal to the application's | — |
| 06 | `workshops/06-agent-loop/tests/` | `cycles` ≥ 2, increasing `tools[].cycle`; independent calls in one cycle; one `step` per call; `cycle_limit_reached` with a mention; interruption without a new call; `interrupted` false otherwise | Answer declared partial at the cycle limit (repeated) |
| 07 | `workshops/07-context-compaction/tests/` | Bounded list, `truncated`, exact `total` quoted; `mode="count"`; `model.calls[].context_size`; no compaction below the threshold; above it: `compaction.summarized_answers`, user messages replayed verbatim, event or mention | Partial result announced (repeated) |
| 08 | `workshops/08-working-memory/tests/` | `state` objects in the trace and in `input.state`; choice between namesakes kept after compaction; unambiguous customer change | — |
| 09 | `workshops/09-mcp/tests/` | Same non-empty catalog for two clients, generic tool (`source`, `filters`), chapter 5 tools removed; `transport="mcp"`, `/sources/` routes only; malformed filter explained; accountant total through `aggregate="total"` equal to the application's | — |
| 10a | `workshops/10a-identity/tests/` | Entry token exchanged (calls as the user, `identity.token_type="application"`); no token, malformed or forged token refused; other organization sees nothing; MCP server refuses calls without a valid entry token | — |
| 10b | `workshops/10b-writes/tests/` | `confirmation_requested.draft_id` of the prepared draft; refused for `read_only`; typed confirmation is not a gesture; one attributed submission after the gesture (`paul-buyer`) | No submission announced before the gesture (repeated) |
| 10c | `workshops/10c-groupings/tests/` | Total and average equal to the application's aggregate; no code-execution tool | Median refused, aggregates offered (repeated) |
| 10d | `workshops/10d-sandboxing/tests/` | Active policy, `is_egress_allowed`; runtime probes: refused host never contacted, no file opened outside `my-agent/` and traces, every host contacted allowed; `limit_reached` with at most one model call and a mention; no secret in the model input, tools or text | — |
| 11 | `workshops/11-architecture/tests/` | `my-agent/trace_queries.py`: exact shares on four example turns, only the incompatible turn reported; queries run on the agent's own trace | — |
| 12 | `workshops/12-long-term-memory/tests/` | Mention about memory on the first turn only; preference absent from a new conversation; order reread from the application | Preference recalled within the conversation (repeated) |
| 13 | `workshops/13-document-search/tests/` | `passages[]` / `no_passage`; `sources` event subset of the passages, version 2.1; empty result declared; audience filtering by role; retired version absent; documentation distinguished from data | — |
| 14 | `workshops/14-skills/tests/` | Manifest of three versioned *skills*; `skills_loaded` before the write; *skill* outside the catalog refused; write tool never offered to `read_only` (`offered_tools`); *skill* kept after compaction | — |
| 15 | `workshops/15-read-without-obeying/tests/` | Attachment read by id; write tools not offered once it is read; no draft nor submission; refused for another conversation; no sending tool; nothing read for one user reaches another | — |
| 16 | `workshops/16-controls/tests/` | Partial-result mention with the total, after a truncated result; customer recorded only after the choice; unverified records listed in a mention; simultaneous conversations with isolated `state` | — |
| 17 | `workshops/17-evaluation/tests/` | Masked and observable traces (`model.usage`, `duration_ms`); official routes published and intact; student routes cover the eight edge cases with a counterfactual; generated `route-report.json`, every route passing k out of n | Meaning layer of each route (repeated) |
| 18 | `workshops/18-failures/tests/` | One submission attempt answered 504, `unknown_outcome.draft_id`; one primary failure then the fallback, `trace.fallback`; `versions` of instructions, tools, *skills*, index | Unknown outcome stated (repeated); fallback stated |
| 19 | `workshops/19-specification/tests/` | Specification with its five parts; checks in `local-mode/controls/` pass, and fail with `MY_AGENT_DISABLE_CONTROL=1`; routes unchanged; reserved part never referenced. The *coding agent* is not required. | — |

## Commands

Run from the repository root. Prepare tooling and test dependencies separately;
the CLI delegates workshop checks to the test project's environment. There is
no root Python project or pytest configuration.

```powershell
uv sync --project workshop_kit/bootstrap --locked --python 3.13
uv sync --project workshop_tests --locked --python 3.13
uv run --project workshop_tests pytest -c workshop_tests/pyproject.toml workshop_kit/tests
uv run --project workshop_kit/bootstrap workshop check 07
uv run --project workshop_kit/bootstrap workshop check 07 --non-regression
uv run --project workshop_kit/bootstrap workshop check-shell
uv run --project workshop_kit/bootstrap workshop check-inert
```

UI tests stay in their own environment (MCP 1, isolated from the test project's MCP 2):

```powershell
uv run --project workshop_kit/chat-ui --extra dev pytest --confcutdir workshop_kit/chat-ui workshop_kit/chat-ui/tests
```
