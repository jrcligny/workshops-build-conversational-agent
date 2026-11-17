# Workshop test inventory

Aligned with the "success criterion" subsections of the book
(`jrcligny/ai-generated-books`, branch `relecture/alignement-ateliers`, not yet merged
into `main`). All these tests **fail against the inert agent** (`workshop check-inert`) and **on the
bootstrap of `my-agent/`** (`workshop check-bootstrap`), except, for the bootstrap, those listed in
`tooling/cli/bootstrap_passes.txt`: the bootstrap already converses through the model. The infrastructure tests in
`<component>/tests/` and `tooling/cli/integration/` must pass. Shared fixtures, clients, runtime probes and evaluation
helpers live in `agent_testkit/` (judge in `agent_testkit.evaluation`), not in the
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
| 04 | `workshops/04-first-tool/tests/` | Exactly one call; `ok` / `approximate` with a suggestion / `not_found` without suggestion for a deleted order; invalid reference rejected before any application call; tool call and result replayed in `input.history` on the next turn | — |
| 05 | `workshops/05-agent-loop/tests/` | Step `outils`: both namesakes returned, no order chosen for the user; `filter="late"` applied by the tool, total equal to the application's. Step `boucle`: `cycles` ≥ 2, increasing `tools[].cycle`, a final answering cycle; independent calls in one cycle; one `step` per call; `cycle_limit_reached` with a mention; interruption without a new call; `interrupted` false otherwise | Answer declared partial at the cycle limit (repeated) |
| 06 | `workshops/06-mcp-server/tests/` | Step `serveur`: same non-empty catalog for two clients, generic tool (`source`, `filters`), chapter 5 tools removed; `transport="mcp"`, `/sources/` routes only; malformed filter explained; accountant total through `aggregate="total"`. Step `regroupements`: grouping by supplier and month (`group_by` list) equal to the application's; no code-execution tool | Median refused, aggregates offered (repeated) |
| 07 | `workshops/07-acting-rights/tests/` | Step `identite`: entry token exchanged (`identity.token_type="application"`); request without identity refused; caches partitioned by organization; MCP server refuses calls without a valid entry token. Step `ecritures`: `confirmation_requested.draft_id`; refused for `read_only`; typed confirmation is not a gesture; one attributed submission after the gesture (`paul-buyer`). Step `confinement`: destination outside the allowlist refused (policy in the test); write turn confined (runtime probes, no secret in model input, tools or text); `limit_reached` with a mention | No submission announced before the gesture (repeated) |
| 09 | `workshops/09-progressive-disclosure/tests/` | Generic query bounded in the MCP server: summarized rows (no detail fields), at most 20; `returned`, `total`, `total_status` (`exact`, or `minimum` at the 200 retrieval cap), `truncated`; next portion through `offset` without repeated rows; count through `aggregate="count"`; detail through the consultation tool; large grouping bounded and declared (private) | Partial result announced |
| 10 | `workshops/10-context-compaction/tests/` | Written conversations loaded (`ChatClient.load`, neutral tools `resolve_name` and `query`), one live turn. No compaction below the threshold; at the threshold: every older tool result cleared (call kept, marker instead of the result), last `kept_turns` replayed, `summarized_turns`, separate model call with `compaction_prompt.md`, rolling summary; `compaction` event or mention; summary judged on its five headings and the tool facts; answer from the summary; `input.state` rebuilt from the loaded conversation; choice between namesakes kept; unambiguous customer change | `10-summary-keeps-tool-facts` |
| 11 | `workshops/11-no-memory/tests/` | `mention` at the opening of each conversation saying nothing is kept, not repeated next turn; no promise to remember; nothing of a previous conversation in the model input; `preference_reports` (`topic`, `value`, planned topics, no user) never reloaded; order reread from the application | No promise, preference limited to the conversation (repeated) |
| 12 | `workshops/12-document-search/tests/` | `passages[]` / `no_passage`; `sources` event subset of the passages, version 2.1; empty result (no passage, no source, explicit declaration); audience filtering by role; retired version absent; documentation distinguished from data | — |
| 13 | `workshops/13-skills/tests/` | Manifest of three versioned *skills*; `skills_loaded` before the write; *skill* outside the catalog refused; write tool never offered to `read_only` (`offered_tools`); *skills* loaded before compaction still in `skills_loaded` and in the model input (set comparison) | — |
| 14 | `workshops/14-read-without-obeying/tests/` | Attachment read by id only if the user can consult its record (`attachments.yaml`, business call on the record), refused otherwise even with the id; write tools still offered up to the cycle reading untrusted content (attachment or trapped documentation passage), withdrawn afterwards; no draft nor submission in that turn; no sending tool | — |
| 15 | `workshops/15-evaluation/tests/` | Masked and observable traces (`model.usage`, `duration_ms`); official routes published and intact; student routes cover the eight edge cases with a counterfactual; routes need a non-textual fact; generated `route-report.json` matches the runs, includes student routes, every route passing k out of n | Meaning layer of each route (repeated) |
| 16 | `workshops/16-failures/tests/` | One submission attempt answered 504, `unknown_outcome.draft_id`, still one after the user asks to retry; one primary failure then the fallback, `trace.fallback`; `versions` of instructions, tools, *skills*, index, stable across turns, `index` changing when the index is rebuilt | Unknown outcome stated (repeated); fallback stated |
| 17 | `workshops/17-specification/tests/` | Specification with its five parts; checks in `local-mode/controls/` pass, and fail with `MY_AGENT_DISABLE_CONTROL=1`; routes unchanged; reserved part never referenced. The *coding agent* is not required. | — |
| bonus | `workshops/bonus-preference-memory/tests/` | Off the path, never in `--non-regression`. Persistent preference memory: written on explicit request (origin, date) under `MEMORY_DIR`; reloaded in a new conversation; partitioned by user and organization; consulted, corrected, forgotten; nothing outside the planned topics; opening mention; order reread | — |

Workshops 05, 06 and 07 run step by step with `workshop check NN --etape <step>`.

## Commands

Run from the repository root. Prepare tooling and test dependencies separately;
the CLI delegates workshop checks to the test project's environment. There is
no root Python project or pytest configuration.

```powershell
uv sync --project tooling/cli --locked --python 3.13
uv sync --project tooling/cli --group tests --locked --python 3.13
uv run --project tooling/cli --group tests pytest -c tooling/cli/pyproject.toml agent_sdk agent_testkit business gateway tooling
uv run --project tooling/cli workshop check 09
uv run --project tooling/cli workshop check 09 --non-regression
uv run --project tooling/cli workshop check-bootstrap
uv run --project tooling/cli workshop check-inert
```

UI tests stay in their own environment (MCP 1, isolated from the test project's MCP 2):

```powershell
uv run --project clients/chat_ui --extra dev pytest --confcutdir clients/chat_ui clients/chat_ui/tests
```
