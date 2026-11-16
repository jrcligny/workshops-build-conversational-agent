# Workshop test inventory

Aligned with the "success criterion" subsections of the book
(`jrcligny/ai-generated-books`, branch `relecture/alignement-ateliers`).
All these tests **fail on the empty shell** (68 tests in total). The
infrastructure tests in `tests/kit/` (40 tests) must pass.

The user turns and expected phrases are French: the agent converses in
French (see `docs/decisions.md`, Language). Judge rubrics fail an answer that
is not in French.

Deterministic checks (application state, traces, permissions, interface
events) come first. The judge, with a written rubric, only steps in when the
traces are not enough to establish the quality of an answer. During design, the
rubric is applied through structural requirements; the meaning assessment is
calibrated in phase B.

| Workshop | Tests folder | Tests (deterministic unless stated) | Judge (rubric) |
|---|---|---|---|
| 03 | `workshops/03-system-prompt/tests/` | Short prompt, no tool nor documentation; no business call; history replayed; text+end+trace contract | Refusal to report on an order, including under insistence (repeated) |
| 04 | `workshops/04-first-tool/tests/` | Exact reference; difference reported for an approximate reference; excluded order never suggested; at most one call; success / missing / error status in the tool result | — |
| 05 | `workshops/05-read-tools/tests/` | All namesakes returned, without choosing for the user; late filter applied by the tool | — |
| 06 | `workshops/06-agent-loop/tests/` | Several cycles; independent calls grouped; steps reported (`step`); interruption without a new call | Answer declared partial at the cycle limit |
| 07 | `workshops/07-context-compaction/tests/` | Bounded list and declared total; count mode; total is a minimum at the cap; context size in the trace; no compaction below the threshold; above it: compaction event, user messages and initial request verbatim, summary of answers and tool results only; reported in the interface | Partial result announced |
| 08 | `workshops/08-working-memory/tests/` | Conversation state in the trace after compaction, distinct from the summary; choice between namesakes kept; unambiguous customer change | — |
| 09 | `workshops/09-mcp/tests/` | Tools served by MCP, no more direct HTTP call from the harness; two clients, same non-empty catalog, chapter 5 tools removed; malformed filter; accountant question through the generic query | — |
| 10a | `workshops/10a-identity/tests/` | Token exchange: the application sees the user, not a service account; `typ=entry` token refused or exchanged | — |
| 10b | `workshops/10b-writes/tests/` | Confirmation requested, draft without effect; preparation refused without permission; submission attributed after the confirmation gesture | No action announced before the submission |
| 10c | `workshops/10c-groupings/tests/` | Grouping computed by the tool; no `exec`/`eval` in the trace | Median refused, aggregates offered |
| 10d | `workshops/10d-sandboxing/tests/` | Sandbox policy (`my-agent/sandbox/policy.yaml`) active and non-empty allowlist; destination outside the list refused; no file access in the trace; turn stopped at the duration/budget limit; secrets absent from the input and the trace | — |
| 11 | `workshops/11-architecture/tests/` | Deliverable `my-agent/trace_queries.py`: `intermediate_reads_share` and `incompatible_domains`, run on `tests/fixtures/example-traces.jsonl` | — |
| 12 | `workshops/12-long-term-memory/tests/` | Announcement on opening; no persistence between conversations; rereads the application rather than assuming | No memory promise |
| 13 | `workshops/13-document-search/tests/` | `sources` event; empty result declared; permission filtering; retired version absent; documentation / data distinction | — |
| 14 | `workshops/14-skills/tests/` | Catalog of three *skills* (`my-agent/skills/manifest.yaml`); loaded before writing; *skill* outside the catalog refused; writes according to permissions; *skill* still present after compaction | — |
| 15 | `workshops/15-read-without-obeying/tests/` | Writes removed after reading a quote (test fixture `tests/fixtures/sample-quote.txt`); read by id; no sending tool; caches not shared between organizations | — |
| 16 | `workshops/16-controls/tests/` | Partial-result mention emitted by the harness; customer recorded only after the choice; unconsulted record marked unverified; simultaneous conversations isolated | — |
| 17 | `workshops/17-evaluation/tests/` | Masked traces (no secret nor authorization header); route report (`my-agent/route-report.md`) covering the edge cases of ch. 17, with repetition and layered judgement | Meaning of the routes: to calibrate in phase B |
| 18 | `workshops/18-failures/tests/` | Submission never replayed (`unknown_outcome` failure); versions (instructions, *skills*, tools, index) in the trace; single switch to the fallback (proxy failure `primary_model`) | Quality of the ending after the fallback fails |
| 19 | `workshops/19-specification/tests/` | Specification and checks in `my-agent/local-mode/`, including a check with a deliberately wrong output; checksum of `workshops/17-evaluation/routes/` unchanged; reserved part out of reach of the local mode. The *coding agent* is not required. | — |

## Commands

```powershell
uv run workshop check 07
uv run workshop check 07 --non-regression
uv run workshop check-shell
```
